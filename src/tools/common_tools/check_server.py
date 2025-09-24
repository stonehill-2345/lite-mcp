"""
Common detection tool utilities
"""

from src.tools.base import BaseMCPServer
from src.core.statistics import mcp_author
import socket
import ssl
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, ec
import ipaddress
import json

@mcp_author("Matthew", email="hhs66317@gmail.com")
class CheckMCPServer(BaseMCPServer):
    """
    Common detection tool utilities
    """

    def __init__(self, name: str = "LiteMCP-Check"):
        # Call parent class initialization to automatically get all transport mode support
        super().__init__(name)
    
    def _register_tools(self):
        """Register tools - supports multiple MCP tools"""

        @self.mcp.tool()
        def check_https_certificate(hostname: str, port: int = 443, ip: str = None, timeout: int = 3) -> str:
            """
            Check HTTPS certificate information

            Args:
                hostname (str): Target domain name (e.g., "www.example.com")
                port (int): Port number (default 443)
                ip (str): Specific server IP address to access (optional)
                timeout (int): Connection timeout in seconds (default 3)

            Returns:
                str: JSON formatted certificate details including validity period, domain matching, issuer information, etc.

            Test scenarios:
                - Normal HTTPS site certificate detection
                - Expired certificate detection
                - Self-signed certificate detection
                - Domain name mismatch certificate detection
                - Access specific server via IP
            """
            try:
                result = self._check_ssl_cert(hostname, port, ip, timeout)
                return json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as e:
                error_result = {
                    "error": True,
                    "message": str(e),
                    "hostname": hostname,
                    "port": port,
                    "ip": ip
                }
                return json.dumps(error_result, ensure_ascii=False, indent=2)

    def _check_ssl_cert(self, hostname, port=443, ip=None, timeout=3):
        """
        Internal method: Check HTTPS certificate information
        """
        # Validate and normalize IP address
        server_ip = None
        if ip:
            try:
                server_ip = str(ipaddress.ip_address(ip))
            except ValueError:
                raise ValueError(f"Invalid IP address: {ip}")

        # Establish raw TCP connection
        connect_to = (server_ip, port) if server_ip else (hostname, port)
        sock = socket.create_connection(connect_to, timeout=timeout)
        
        # Create SSL context and get certificate
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Use SNI extension to ensure getting certificate for target domain
        ssl_sock = context.wrap_socket(
            sock, 
            server_hostname=hostname,
            do_handshake_on_connect=True
        )
        
        # Get certificate in binary format
        der_cert = ssl_sock.getpeercert(binary_form=True)
        ssl_sock.close()
        
        # Parse certificate using cryptography
        cert = x509.load_der_x509_certificate(der_cert, default_backend())
        
        # Get current time
        now = datetime.now(timezone.utc)
        not_valid_before = cert.not_valid_before_utc
        not_valid_after = cert.not_valid_after_utc
        
        # Calculate certificate status
        valid = not_valid_before <= now <= not_valid_after
        expired = now > not_valid_after
        days_remaining = (not_valid_after - now).days if not_valid_after > now else 0
        
        # Parse subject information
        subject = {}
        for attr in cert.subject:
            # Get attribute name (use OID if not available)
            name = getattr(attr.oid, '_name', f'OID.{attr.oid.dotted_string}')
            subject[name] = attr.value
        
        # Parse issuer information
        issuer = {}
        for attr in cert.issuer:
            name = getattr(attr.oid, '_name', f'OID.{attr.oid.dotted_string}')
            issuer[name] = attr.value
        
        # Parse Subject Alternative Names (SAN)
        san_entries = []
        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            for name in san.value:
                if isinstance(name, x509.DNSName):
                    san_entries.append(name.value)
        except x509.ExtensionNotFound:
            pass
        
        # Check if domain name matches certificate
        hostname_match = any(
            self._matches_hostname(name, hostname) 
            for name in san_entries + [subject.get("commonName", "")]
        )
        
        # Parse key information
        public_key = cert.public_key()
        key_info = {
            "algorithm": None,
            "key_size": None
        }
        
        # RSA key
        if isinstance(public_key, rsa.RSAPublicKey):
            key_info["algorithm"] = "RSA"
            key_info["key_size"] = public_key.key_size
            
        # ECC key
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            key_info["algorithm"] = "ECC"
            key_info["key_size"] = public_key.curve.key_size
            
        # Other key types
        else:
            key_info["algorithm"] = "Unknown"
        
        # Signature algorithm
        signature_hash_algorithm = cert.signature_hash_algorithm
        signature_algorithm = (
            f"{signature_hash_algorithm.name.upper()}" 
            if signature_hash_algorithm else "UNKNOWN"
        )
        
        # Get resolved IP address
        resolved_ip = server_ip
        if not resolved_ip:
            try:
                resolved_ip = socket.gethostbyname(hostname)
            except:
                resolved_ip = "Unable to resolve"
        
        # Return complete result
        return {
            "error": False,
            "hostname": hostname,
            "resolved_ip": resolved_ip,
            "port": port,
            "valid": valid,
            "expired": expired,
            "not_valid_before": not_valid_before.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "not_valid_after": not_valid_after.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "days_remaining": days_remaining,
            "hostname_match": hostname_match,
            "subject": subject,
            "issuer": issuer,
            "serial_number": str(cert.serial_number),
            "version": cert.version.name.replace("v", "") if hasattr(cert.version, 'name') else "Unknown",
            "signature_algorithm": signature_algorithm,
            "public_key": key_info,
            "subject_alt_names": san_entries,
            "certificate_summary": self._generate_cert_summary(valid, expired, days_remaining, hostname_match)
        }

    def _matches_hostname(self, cert_name, hostname):
        """Check if the name in certificate matches the target hostname"""
        if not cert_name:
            return False
            
        cert_name = cert_name.lower()
        hostname = hostname.lower()
        
        # Handle wildcard certificates
        if cert_name.startswith("*."):
            # Get domain part after wildcard
            domain = cert_name[2:]  # Remove "*."
                        
            if hostname == domain:
                # Wildcard does not match root domain, e.g., *.baidu.com does not match baidu.com
                return False
            
            if hostname.endswith("." + domain):
                # Check if it is a direct subdomain (not multi-level subdomain)
                prefix = hostname[:-len("." + domain)]
                # If prefix part does not contain dots, it is a direct subdomain
                return "." not in prefix
            
            return False
        
        # Exact match
        return cert_name == hostname

    def _generate_cert_summary(self, valid, expired, days_remaining, hostname_match):
        """Generate certificate status summary"""
        summary = []
        
        if expired:
            summary.append("❌ Certificate expired")
        elif not valid:
            summary.append("❌ Certificate not yet valid")
        elif days_remaining < 7:
            summary.append(f"⚠️ Certificate expiring soon ({days_remaining} days)")
        elif days_remaining < 30:
            summary.append(f"⚠️ Certificate expires within 30 days ({days_remaining} days)")
        else:
            summary.append(f"✅ Certificate valid ({days_remaining} days remaining)")
        
        if not hostname_match:
            summary.append("❌ Domain name mismatch")
        else:
            summary.append("✅ Domain name matches")
        
        return " | ".join(summary)


# Create global instance for framework use
pc_server = CheckMCPServer()

# If running this file directly, start the server
if __name__ == "__main__":
    # Support all transport modes:
    # pc_server.run()       # STDIO mode
    # pc_server.run_http()  # HTTP mode
    # pc_server.run_sse()   # SSE mode
    pc_server.run()