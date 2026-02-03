/**
 * Authentication utilities and route protection
 */

export const isAuthenticated = (): boolean => {
  const token = localStorage.getItem('access_token');
  return !!token;
};

export const clearAuth = (): void => {
  localStorage.removeItem('access_token');
  // Clear any other auth-related data
  sessionStorage.clear();
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token');
};

export const setAuthToken = (token: string): void => {
  localStorage.setItem('access_token', token);
};

export const logout = async (): Promise<void> => {
  const token = getAuthToken();
  
  if (token) {
    try {
      // Call backend logout endpoint
      await fetch('http://localhost:8000/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local cleanup even if API call fails
    }
  }
  
  // Clear local auth data
  clearAuth();
};
