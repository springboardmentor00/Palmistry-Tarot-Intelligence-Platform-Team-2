// Central API base URL pointing to FastAPI backend
const API_BASE_URL = 'http://localhost:8000';

// Helper function to attach JWT token to authorized requests
const getAuthHeaders = () => {
  const token = localStorage.getItem('jwt_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// --- AUTHENTICATION APIS ---
export async function loginUser(credentials) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await response.json();
  if (data.access_token) {
    localStorage.setItem('jwt_token', data.access_token);
  }
  return data;
}

export async function getUserProfile() {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  });
  if (!response.ok) throw new Error('Failed to fetch profile');
  return await response.json();
}

// --- PALM ANALYSIS API ---
export async function analyzePalmImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/palm/analyze`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(), // Pass JWT token
    },
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Palm analysis failed');
  }
  return await response.json();
}

// --- TAROT READING API ---
export async function drawTarotCards(spreadType) {
  const response = await fetch(`${API_BASE_URL}/api/tarot/draw`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(), // Pass JWT token
    },
    body: JSON.stringify({ spread_type: spreadType }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Tarot draw failed');
  }
  return await response.json();
}