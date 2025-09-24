import { ElMessage } from 'element-plus'

/**
 * Clipboard operation hooks
 */
export function useClipboard() {
  /**
   * Copy text to clipboard
   * @param {string} text - Text to copy
   * @param {string} successMsg - Success message, default is "Copy successful"
   * @param {string} errorMsg - Error message, default is "Copy failed"
   * @returns {Promise<boolean>} - Returns whether copy was successful
   */
  const copyToClipboard = async (text, successMsg = "Copy successful", errorMsg = "Copy failed") => {
    try {
      // Prefer modern Clipboard API
      await navigator.clipboard.writeText(text)
      ElMessage.success(successMsg)
      return true
    } catch (clipboardError) {
      // Fallback to traditional method - refer to data.js implementation
      try {
        const input = document.createElement('textarea')
        input.value = text
        input.style.position = 'fixed'  // Avoid page scrolling
        input.style.opacity = '0'       // Hide input box
        input.style.left = '-999999px' // Move out of viewport
        input.style.top = '-999999px'
        document.body.appendChild(input)
        input.select()

        const success = document.execCommand('copy')
        document.body.removeChild(input)

        if (success) {
          ElMessage.success(successMsg)
          return true
        } else {
          throw new Error('execCommand copy failed')
        }
      } catch (error) {
        ElMessage.error(errorMsg)
        console.error('Failed to copy to clipboard:', error)
        return false
      }
    }
  }

  /**
   * Read text from clipboard
   * @returns {Promise<string>}
   */
  const readFromClipboard = async () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        return await navigator.clipboard.readText()
      } else {
        throw new Error('This browser does not support reading from clipboard')
      }
    } catch (error) {
      ElMessage.error('Failed to read from clipboard')
      console.error('Failed to read from clipboard:', error)
      throw error
    }
  }

  /**
   * Check if clipboard operations are supported
   * @returns {boolean}
   */
  const isClipboardSupported = () => {
    return !!(navigator.clipboard || document.execCommand)
  }

  return {
    copyToClipboard,
    readFromClipboard,
    isClipboardSupported
  }
}