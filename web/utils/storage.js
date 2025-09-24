import Cookies from 'js-cookie'

export const getCookies = (key, defaultValue) => {
    try {
        return Cookies.get(key) && Cookies.get(key) !== 'undefined'
            ? JSON.parse(Cookies.get(key))
            : defaultValue
    } catch (e) {
        return Cookies.get(key)
    }
}

export const setCookies = (key, value) =>
    Cookies.set(key, JSON.stringify(value))

export const removeCookies = (key) => Cookies.remove(key)
export const removeLocalStorage = (key) => localStorage.removeItem(key)

export function getCacheByKey(key) {
    try {
        // Check localStorage first
        const localValue = localStorage.getItem(key)
        if (localValue !== null) {
            return JSON.parse(localValue)
        }
        
        // Then check sessionStorage
        const sessionValue = sessionStorage.getItem(key)
        if (sessionValue !== null) {
            return JSON.parse(sessionValue)
        }
        
        // Not found in either, return null
        return null
    } catch (error) {
        console.error(`getCacheByKey parsing error [${key}]:`, error)
        return null
    }
}

export function setCache(key, val) {
    const strVal = JSON.stringify(val)
    return localStorage.setItem(key, strVal) || sessionStorage.setItem(key, strVal)
}