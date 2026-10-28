const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const TOKEN_KEY = 'ckd_access_token';
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);
export async function apiRequest(path, {method='GET', body, token=getToken(), headers={}, isForm=false, responseType='json'}={}) {
  const requestHeaders = {...headers};
  if (token) requestHeaders.Authorization = `Bearer ${token}`;
  if (body !== undefined && !isForm && responseType === 'json') requestHeaders['Content-Type'] = 'application/json';
  const response = await fetch(`${API_BASE}${path}`, {method, headers:requestHeaders, ...(body !== undefined ? {body: isForm ? body : JSON.stringify(body)} : {})});
  if (responseType === 'blob') {
    if (!response.ok) { let detail=`Request failed (${response.status})`; try { const d=await response.json(); detail=d.detail||detail; } catch {} throw new Error(detail); }
    return response.blob();
  }
  const data = await response.json().catch(()=>({}));
  if (!response.ok) throw new Error(typeof data.detail==='string' ? data.detail : JSON.stringify(data.detail || data) || `Request failed (${response.status})`);
  return data;
}
export function downloadBlob(blob, filename) {
  const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export const apiConfig = {API_BASE};
