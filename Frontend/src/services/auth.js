import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:4001/api/v1';

// Set up axios defaults
axios.defaults.baseURL = API_BASE_URL;

// Add token to requests if available
axios.interceptors.request.use((config ) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login = async (username, password) => {
  try {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await axios.post('/login/access-token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    return { success: true };
  } catch (error) {
    return { 
      success: false, 
      error: error.response?.data?.detail || 'Login failed' 
    };
  }
};

export const logout = () => {
  localStorage.removeItem('token');
  window.location.href = '/login';
};

export const isAuthenticated = () => {
  const token = localStorage.getItem('token');
  if (!token) return false;
  
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp > Date.now() / 1000;
  } catch {
    return false;
  }
};

export const getCurrentUser = async () => {
  try {
    const response = await axios.get('/users/me');
    return response.data;
  } catch (error) {
    logout();
    return null;
  }
};
