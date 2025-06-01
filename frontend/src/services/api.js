import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8766',
  headers: {
    'Content-Type': 'application/json',
    'x-meeting-baas-api-key': import.meta.env.VITE_MEETING_BAAS_API_KEY,
  }
});

// Endpoints that are expected to potentially return 404 (under development)
const DEVELOPMENT_ENDPOINTS = ['/active-bots'];

// API service methods
const apiService = {
  // Personas
  getPersonas: () => api.get('/personas'),
  getPersona: (id) => api.get(`/personas/${id}`),
  createPersona: (data) => api.post('/personas', data),
  updatePersona: (id, data) => api.put(`/personas/${id}`, data),
  deletePersona: (id) => api.delete(`/personas/${id}`),
  
  // Bots
  getBots: () => api.get('/bots'),
  getBot: (id) => api.get(`/bots/${id}`),
  createBot: (data) => api.post('/bots', data),
  stopBot: (id) => api.post(`/bots/${id}/stop`),
  
  // Active bots
  getActiveBots: () => api.get('/active-bots'),
};

// Helper function to extract error message from various formats
const extractErrorMessage = (error) => {
  // If it's a direct message string
  if (typeof error?.response?.data === 'string') {
    return error.response.data;
  }
  
  // If it's a FastAPI validation error with detail array
  if (Array.isArray(error?.response?.data?.detail)) {
    return error.response.data.detail
      .map(err => `${err.loc?.join('.')} - ${err.msg}`)
      .join('; ');
  }
  
  // If it's a FastAPI error with detail string
  if (error?.response?.data?.detail) {
    return typeof error.response.data.detail === 'object'
      ? JSON.stringify(error.response.data.detail)
      : error.response.data.detail;
  }
  
  // Default message
  return 'An unknown error occurred';
};

// Check if a URL is in the list of development endpoints
const isDevEndpoint = (url) => {
  if (!url) return false;
  return DEVELOPMENT_ENDPOINTS.some(endpoint => url.includes(endpoint));
};

// Response interceptor for handling common error cases
api.interceptors.response.use(
  response => response,
  error => {
    // Don't log errors for endpoints that are known to be under development
    const isExpected404 = error.response?.status === 404 && isDevEndpoint(error.config?.url);
    
    if (!isExpected404) {
      // Only log errors for unexpected conditions
      console.error('API Error:', error.response || error);
    }
    
    const errorMessage = extractErrorMessage(error);
    
    // Return a rejected promise with the error information
    return Promise.reject({
      status: error.response?.status,
      message: errorMessage,
      originalError: error
    });
  }
);

export default apiService; 