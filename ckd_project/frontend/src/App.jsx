import React, {useEffect, useMemo, useState} from 'react';
import {Activity, AlertCircle, Bell, BookOpen, CalendarDays, Check, ChevronDown, ChevronLeft, ChevronRight, ClipboardList, Download, FileText, Filter, HeartPulse, LayoutDashboard, LockKeyhole, LogOut, Menu, Moon, Plus, Search, Settings, ShieldCheck, Sun, Users, X, Upload, UserCheck, Clock3} from 'lucide-react';
import {Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import {apiRequest, setToken, getToken, downloadBlob} from './api';
import ClinicalAssistant from './ClinicalAssistant';
const riskColors = {
  HIGH: '#e45c65', High: '#e45c65',
  MEDIUM: '#e8a23c', Medium: '#e8a23c',
  LOW: '#22a783', Low: '#22a783',
  Unknown: '#94a3b8', Unassessed: '#94a3b8'
};

// Keep backend risk labels intact in meaning while comparing/displaying them consistently.
function normalizeRisk(value) {
  const risk = String(value ?? '').trim().toLowerCase();
  if (risk === 'high') return 'High';
  if (risk === 'medium') return 'Medium';
  if (risk === 'low') return 'Low';
  return 'Unassessed';
}

function isRiskMatch(patientRisk, selectedRisk) {
  return selectedRisk === 'All' || normalizeRisk(patientRisk) === normalizeRisk(selectedRisk);
}

// Format the current local date for <input type="date"> without UTC timezone shifts.
function getLocalDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function isValidDate(value) {
  return typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Date.parse(value));
}

// Mirrors the frontend's supported report periods; invalid/missing dates are excluded
// from bounded periods, but remain included when Period is All.
function isWithinReportPeriod(dateValue, period, now = new Date()) {
  if (period === 'All') return true;
  if (!isValidDate(dateValue)) return false;
  const months = { 'Last month': 1, '3 months': 3, '6 months': 6, '12 months': 12 }[period];
  if (!months) return true;
  const cutoff = new Date(now);
  cutoff.setMonth(cutoff.getMonth() - months);
  const date = new Date(dateValue);
  return date <= now && date >= cutoff;
}
const initialSettings={alerts:true,followups:true,weekly:true,system:true};
function initials(n='User'){return String(n).trim().split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase() || 'U'}
function mapPatient(p){
 const labs=(p.visits||[]).flatMap(v=>(v.lab_results||v.lab_result?[...(v.lab_results||[v.lab_result])].filter(Boolean).map(l=>({...l,visit_date:v.visit_date,visit_id:v.visit_id})):[])).sort((a,b)=>String(b.visit_date||'').localeCompare(String(a.visit_date||'')));
 const latest=labs[0]||{};
 const gender=p.gender===1?'Male':p.gender===2?'Female':p.gender===3?'Other':'Not specified';
 return {id:p.patient_id,name:p.full_name||p.display_name||p.patient_id,age:p.age_at_baseline,gender,source:p.source_code,source_patient_id:p.source_patient_id,
   diabetes:!!p.diabetes,hypertension:!!p.hypertension,cvd:!!p.cvd,ihd:!!p.ihd,dyslipidemia:!!p.dyslipidemia,
   egfr:latest.egfr_ml_min_1_73m2 ?? p.baseline_egfr ?? null,acr:latest.acr_mg_g ?? p.baseline_albuminuria ?? null,
   creatinine:latest.creatinine_mg_dl ?? null,bmi:p.baseline_bmi ?? null,hba1c:latest.hba1c_percent ?? null,
   bp:(latest.sbp_mmhg!=null&&latest.dbp_mmhg!=null)?`${latest.sbp_mmhg} / ${latest.dbp_mmhg}`:(p.baseline_sbp!=null&&p.baseline_dbp!=null?`${p.baseline_sbp} / ${p.baseline_dbp}`:'—'),
   risk:String(p.latest_analysis?.risk_level ?? '').trim() || 'Unassessed', visits:(p.visits||[]).map(v=>{const l=(v.lab_results||v.lab_result?[...(v.lab_results||[v.lab_result])].filter(Boolean):[])[0]||{};return {date:v.visit_date,egfr:l.egfr_ml_min_1_73m2,acr:l.acr_mg_g,creatinine:l.creatinine_mg_dl,bp:l.sbp_mmhg!=null&&l.dbp_mmhg!=null?`${l.sbp_mmhg}/${l.dbp_mmhg}`:'—',hb:l.hemoglobin_g_dl,potassium:l.potassium_mmol_l};}).sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')))};
}
function Button({children,kind='secondary',...props}){return <button className={`btn ${kind}`} {...props}>{children}</button>}
function PageTitle({eyebrow,title,subtitle,actions}){return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{subtitle&&<p>{subtitle}</p>}</div>{actions&&<div className="title-actions">{actions}</div>}</div>}
function Panel({title,subtitle,children,actions}){return <section className="panel"><div className="panel-heading"><div><h3>{title}</h3>{subtitle&&<p>{subtitle}</p>}</div>{actions}</div>{children}</section>}
function Tag({children}){const c=String(children||'Unknown').toLowerCase().replace(/[^a-z]/g,'-');return <span className={`tag tag-${c}`}>{children}</span>}

function Login({ onLogin, onRegister, loading, error }) {
  const [tab, setTab] = useState('Login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('DOCTOR');
  const [password, setPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [formError, setFormError] = useState('');
  //replaced  code
  useEffect(() => {
  const params = new URLSearchParams(
    window.location.hash.replace(/^#/, "")
  );

  const token = params.get("reset_token");

  if (token) {
    setResetToken(token);
    setTab("Reset");

    // Remove the token from the address bar after capturing it.
    window.history.replaceState(
      null,
      "",
      window.location.pathname + window.location.search
    );
  }
}, []);

  

async function requestReset(e) {
  e.preventDefault();
  setBusy(true);
  setMessage('');
  setFormError('');

  try {
    const result = await apiRequest('/auth/forgot-password', {
      method: 'POST',
      body: { email: email.trim() },
      token: null,
    });

    setMessage(
      result.message ||
        'If the account exists, reset instructions have been generated. Check the backend terminal.'
    );
  } catch (err) {
    setFormError(err.message || 'Unable to request a password reset.');
  } finally {
    setBusy(false);
  }
}


  async function submitNewPassword(e) {
    e.preventDefault();
    setMessage('');
    setFormError('');

    if (newPassword.length < 10 || newPassword.length > 128) {
      setFormError('Password must be between 10 and 128 characters.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setFormError('The passwords do not match.');
      return;
    }

    setBusy(true);
    try {
      const result = await apiRequest('/auth/reset-password', {
        method: 'POST',
        body: { token: resetToken, new_password: newPassword },
        token: null
      });
      setMessage(result.message);
      setPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setResetToken('');
      setTab('Login');
    } catch (err) {
      setFormError(err.message || 'Unable to reset password.');
    } finally {
      setBusy(false);
    }
  }

  const heading = {
    Login: 'Welcome back',
    'Sign Up': 'Create an account',
    Forgot: 'Reset your password',
    Reset: 'Choose a new password'
  }[tab];

  const subtitle = {
    Login: 'Sign in to your workspace.',
    'Sign Up': 'Doctor and DEO accounts require Admin approval.',
    Forgot: 'We will email a reset link if an account matches.',
    Reset: 'Choose a new password for your CKD Care account.'
  }[tab];
  return (
    <div className="login-page">
      <section className="login-card">
        <div className="login-visual">
          <div className="brand">
            <span className="brand-mark"><HeartPulse /></span>
            <div>
              <b>CKD Care</b>
              <small>Clinical decision support</small>
            </div>
          </div>
          <div className="kidney-art"><Activity size={78} /></div>
          <div className="visual-copy">
            <p className="eyebrow">CLINICAL INTELLIGENCE, WITH CARE</p>
            <h1>Better insights.<br />Better kidney health.</h1>
            <p>
              Review patient records, longitudinal laboratory history and
              progression analysis in one workspace.
            </p>
            <div className="benefit"><Check size={16} /> Database-backed patient records</div>
            <div className="benefit"><Check size={16} /> Secure role-controlled access</div>
            <div className="benefit"><Check size={16} /> Clinical reports for review</div>
          </div>
          <div className="visual-footer">
            Clinical decision support · Clinician remains responsible for interpretation.
          </div>
        </div>

        <div className="login-form-wrap">
          <div className="form-heading">
            <span className="eyebrow">WELCOME TO CKD CARE</span>
            <h2>{heading}</h2>
            <p>{subtitle}</p>
          </div>

          {['Login', 'Sign Up'].includes(tab) && (
            <div className="auth-tabs">
              <button
                type="button"
                className={tab === 'Login' ? 'selected' : ''}
                onClick={() => {
                  setTab('Login');
                  setMessage('');
                  setFormError('');
                }}
              >
                Login
              </button>
              <button
                type="button"
                className={tab === 'Sign Up' ? 'selected' : ''}
                onClick={() => {
                  setTab('Sign Up');
                  setMessage('');
                  setFormError('');
                }}
              >
                Sign Up
              </button>
            </div>
          )}

          {tab === 'Login' && (
            <form onSubmit={async e => {
              e.preventDefault();
              await onLogin({ username, email, password });
            }}>
              <label>
                Username or email
                <input
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  autoComplete="username"
                  placeholder="Enter username or email"
                />
              </label>
              <label>
                Email address (optional)
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="Use this or username"
                  autoComplete="email"
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  minLength={10}
                  autoComplete="current-password"
                />
              </label>
              {error && <p className="form-error">{error}</p>}
              {message && <p>{message}</p>}
              {formError && <p className="form-error">{formError}</p>}
              <button className="btn primary full" type="submit" disabled={loading}>
                {loading ? 'Please wait…' : 'Sign in'} <ChevronRight size={16} />
              </button>
              <p>
                <button
                  className="table-link"
                  type="button"
                  onClick={() => {
                    setEmail('');
                    setMessage('');
                    setFormError('');
                    setTab('Forgot');
                  }}
                >
                  Forgot password?
                </button>
              </p>
            </form>
          )}

          {tab === 'Sign Up' && (
            <form onSubmit={async e => {
              e.preventDefault();
              await onRegister({ username, email, password, full_name: name, role });
            }}>
              <label>
                Full name
                <input value={name} onChange={e => setName(e.target.value)} required maxLength={150} />
              </label>
              <label>
                Username
                <input value={username} onChange={e => setUsername(e.target.value)} required minLength={3} maxLength={100} />
              </label>
              <label>
                Email address
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" />
              </label>
              <label>
                Requested role
                <select value={role} onChange={e => setRole(e.target.value)}>
                  <option value="DOCTOR">Doctor</option>
                  <option value="DEO">Data Entry Operator (DEO)</option>
                </select>
              </label>
              <label>
                Password
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={10} maxLength={128} autoComplete="new-password" />
              </label>
              {error && <p className="form-error">{error}</p>}
              <button className="btn primary full" type="submit" disabled={loading}>
                {loading ? 'Please wait…' : 'Create account'} <ChevronRight size={16} />
              </button>
            </form>
          )}

          {tab === 'Forgot' && (
            <form onSubmit={requestReset}>
              <label>
                Account email address
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </label>
              {message && <p>{message}</p>}
              {formError && <p className="form-error">{formError}</p>}
              <button className="btn primary full" type="submit" disabled={busy}>
                {busy ? 'Submitting…' : 'Send reset link'}
              </button>
              <p>
                <button type="button" className="table-link" onClick={() => {
                  setTab('Login');
                  setMessage('');
                  setFormError('');
                }}>
                  Back to login
                </button>
              </p>
            </form>
          )}

          {tab === 'Reset' && (
            <form onSubmit={submitNewPassword}>
              {!resetToken && (
                <p className="form-error">
                  The reset token is missing. Request a new reset link.
                </p>
              )}
              <label>
                New password
                <input
                  type="password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  required
                  minLength={10}
                  maxLength={128}
                  autoComplete="new-password"
                />
              </label>
              <label>
                Confirm new password
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  required
                  minLength={10}
                  maxLength={128}
                  autoComplete="new-password"
                />
              </label>
              {message && <p>{message}</p>}
              {formError && <p className="form-error">{formError}</p>}
              <button className="btn primary full" type="submit" disabled={busy || !resetToken}>
                {busy ? 'Changing password…' : 'Change password'}
              </button>
            </form>
          )}

          <p className="login-legal">
            Pending accounts cannot access patient data. Do not use this student
            project for real patient-care decisions without security, privacy
            and clinical validation.
          </p>
        </div>
      </section>
    </div>
  );
}

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('ckd-theme') || 'light');
  const [token, setTok] = useState(getToken());
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState('Dashboard');
  const [patients, setPatients] = useState([]);
  const [query, setQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('All');
  const [sort, setSort] = useState('Recent');
  const [selectedId, setSelectedId] = useState(null);
  const [toast, setToast] = useState('');
  const [mobileNav, setMobileNav] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [profile, setProfile] = useState({ full_name: '', email: '', hospital: '' });
  const [profileBusy, setProfileBusy] = useState(false);
  const [modal, setModal] = useState('');
  const [patientForm, setPatientForm] = useState({});
  const [visitForm, setVisitForm] = useState({});
  const [resourceForm, setResourceForm] = useState({
    title: '',
    category: 'Guidelines',
    source_name: '',
    source_url: '',
    version_label: '',
    file: null
  });
  const [resources, setResources] = useState([]);
  const [reportFilter, setReportFilter] = useState({
    risk: 'All',
    source: 'All',
    search: '',
    period: '12 months'
  });
  const [reportTab, setReportTab] = useState('Risk Distribution');
  const [chartData, setChartData] = useState([]);
  const [settings, setSettings] = useState(initialSettings);
  const [adminPending, setAdminPending] = useState([]);

  const notify = m => {
    setToast(m);
    window.setTimeout(() => setToast(''), 3500);
  };

  const persistTheme = v => {
    setTheme(v);
    localStorage.setItem('ckd-theme', v);
  };

  const go = v => {
    setPage(v);
    setMobileNav(false);
    setShowNotifications(false);
  };

  const request = async (path, opts = {}) =>
    apiRequest(path, {
      ...opts,
      token: opts.token === undefined ? getToken() : opts.token
    });

  async function loadPatients() {
    const d = await request('/patients?limit=250');
    const rows = (d.items || d.patients || d || []).map(mapPatient);
    setPatients(rows);

    if (!selectedId && rows[0]) {
      setSelectedId(rows[0].id);
    }
  }

  async function loadNotifications() {
    try {
      const d = await request('/notifications');
      setNotifications(d.items || d || []);
    } catch (e) {
      notify(`Notifications: ${e.message}`);
    }
  }

  async function loadResources() {
    try {
      const d = await request('/resources');
      setResources(d.items || d || []);
    } catch (e) {
      notify(`Resources: ${e.message}`);
    }
  }

  // Manual RAG indexing: indexing is deliberately separate from upload.
  async function indexResource(resourceId) {
    try {
      const data = await request(
        `/clinical-assistant/index/${resourceId}`,
        { method: 'POST' }
      );
      await loadResources();
      notify(`Indexed ${data.chunks_indexed} passages.`);
    } catch (e) {
      notify(`Indexing failed: ${e.message}`);
    }
  }

  async function loadProfile() {
    const d = await request('/profile');

    setProfile({
      full_name: d.full_name || '',
      email: d.email || '',
      hospital: d.hospital || ''
    });

    setUser(d);
  }

  async function loadAdmin() {
    if (user?.role !== 'ADMIN') return;

    try {
      const d = await request('/admin/users/pending');
      setAdminPending(d.items || d || []);
    } catch (e) {
      notify(e.message);
    }
  }

  // Authentication errors are handled separately from secondary API failures.
  async function boot(t) {
    let me;

    try {
      me = await apiRequest('/auth/me', { token: t });
    } catch (e) {
      setToken(null);
      setTok(null);
      setUser(null);
      setError(e.message || 'Your session has expired. Please sign in again.');
      return;
    }

    setUser(me);
    setTok(t);

    const results = await Promise.allSettled([
      loadPatients(),
      loadNotifications(),
      loadResources()
    ]);

    try {
      await loadProfile();
    } catch (e) {
      notify(`Profile could not be loaded: ${e.message}`);
    }

    if (results[0].status === 'rejected') {
      notify(
        `Signed in successfully, but patient data could not load: ${
          results[0].reason?.message || 'Check the backend connection.'
        }`
      );
    }
  }

  useEffect(() => {
    if (token) boot(token);
  }, []);

  useEffect(() => {
    if (user?.role === 'ADMIN') loadAdmin();
  }, [user?.role]);

  useEffect(() => {
    const handler = e => go(e.detail);
    window.addEventListener('ckd-go-page', handler);
    return () => window.removeEventListener('ckd-go-page', handler);
  }, []);

  // Dashboard and Patients share their existing search/risk controls. Reports use
  // reportFilteredPatients below and never inherit these global filters.
  const allFiltered = useMemo(() => {
    const riskOrder = { High: 0, Medium: 1, Low: 2, Unassessed: 3 };
    const normalizedQuery = query.trim().toLowerCase();

    return patients
      .filter(patient => {
        const matchesSearch = !normalizedQuery ||
          `${patient.name} ${patient.id} ${patient.source ?? ''}`
            .toLowerCase()
            .includes(normalizedQuery);
        return matchesSearch && isRiskMatch(patient.risk, riskFilter);
      })
      .sort((a, b) => {
        if (sort === 'Name') return String(a.name).localeCompare(String(b.name));
        if (sort === 'Risk') {
          return riskOrder[normalizeRisk(a.risk)] - riskOrder[normalizeRisk(b.risk)];
        }
        return String(b.id).localeCompare(String(a.id));
      });
  }, [patients, query, riskFilter, sort]);

  // Reports have an independent cohort. A bounded period includes patients with at
  // least one valid visit date in that window; All retains records with missing dates.
  const reportFilteredPatients = useMemo(() => {
    const normalizedSearch = reportFilter.search.trim().toLowerCase();
    return patients.filter(patient => {
      const matchesRisk = isRiskMatch(patient.risk, reportFilter.risk);
      const matchesSource = reportFilter.source === 'All' ||
        patient.source === reportFilter.source;
      const matchesSearch = !normalizedSearch ||
        `${patient.name} ${patient.id}`.toLowerCase().includes(normalizedSearch);
      const matchesPeriod = reportFilter.period === 'All' ||
        patient.visits.some(visit => isWithinReportPeriod(visit.date, reportFilter.period));
      return matchesRisk && matchesSource && matchesSearch && matchesPeriod;
    });
  }, [patients, reportFilter]);

  // Visits used by report charts/statistics are restricted to the same report period.
  const reportVisits = useMemo(() => reportFilteredPatients.flatMap(patient =>
    patient.visits
      .filter(visit => isWithinReportPeriod(visit.date, reportFilter.period))
      .map(visit => ({ ...visit, patientId: patient.id, patientName: patient.name }))
  ), [reportFilteredPatients, reportFilter.period]);

  const reportRiskCounts = useMemo(() => {
    const counts = { High: 0, Medium: 0, Low: 0, Unassessed: 0 };
    reportFilteredPatients.forEach(patient => { counts[normalizeRisk(patient.risk)] += 1; });
    return counts;
  }, [reportFilteredPatients]);

  const reportMeanEgfr = useMemo(() => {
    const values = reportFilteredPatients
      .map(patient => Number(patient.egfr))
      .filter(value => Number.isFinite(value));
    return values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(1) : '—';
  }, [reportFilteredPatients]);

  const reportHighAcrCount = reportFilteredPatients.filter(
    patient => patient.acr != null && Number.isFinite(Number(patient.acr)) && Number(patient.acr) >= 300
  ).length;
  const reportPatientsWithVisits = reportFilteredPatients.filter(patient =>
    patient.visits.some(visit => isWithinReportPeriod(visit.date, reportFilter.period))
  ).length;

  const selected =
    patients.find(p => p.id === selectedId) || allFiltered[0] || null;

  async function login(payload) {
    setLoading(true);
    setError('');

    try {
      const identity = (payload.email || payload.username || '').trim();

      const body = identity.includes('@')
        ? { email: identity, password: payload.password }
        : { username: identity, password: payload.password };

      const res = await apiRequest('/auth/login', {
        method: 'POST',
        body,
        token: null
      });

      setToken(res.access_token);
      setTok(res.access_token);

      await boot(res.access_token);
      notify('Signed in.');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function register(payload) {
    setLoading(true);
    setError('');

    try {
      const res = await apiRequest('/auth/register', {
        method: 'POST',
        body: payload,
        token: null
      });

      setError(
        res.message ||
          'Account created. An Admin must approve it before sign-in.'
      );

      notify('Registration complete. Wait for Admin approval.');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function signOut() {
    setToken(null);
    setTok(null);
    setUser(null);
    setPatients([]);
    setPage('Dashboard');
  }

  async function assessPatient(patientId) {
    setLoading(true);
    try {
      const result = await request(`/patients/${encodeURIComponent(patientId)}/analyze`, { method: 'POST' });
      await loadPatients();
      notify(`Assessment completed: ${result.risk_level || 'UNASSESSED'} risk · ${result.prioritization?.priority || 'Priority unavailable'}. Review the analysis before making clinical decisions.`);
    } catch (e) {
      notify(`Assessment failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function savePatient(e) {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        patient_id: patientForm.editing ? patientForm.patient_id : undefined,
        full_name: patientForm.full_name,
        source_code: patientForm.source_code || 'HOSP',
        source_patient_id: patientForm.editing ? patientForm.source_patient_id : undefined,
        age_at_baseline:
          patientForm.age_at_baseline === ''
            ? null
            : Number(patientForm.age_at_baseline),
        gender:
          patientForm.gender === '' ? null : Number(patientForm.gender),
        diabetes: !!patientForm.diabetes,
        hypertension: !!patientForm.hypertension,
        ihd: !!patientForm.ihd,
        cvd: !!patientForm.cvd,
        dyslipidemia: !!patientForm.dyslipidemia,
        baseline_sbp:
          patientForm.baseline_sbp === ''
            ? null
            : Number(patientForm.baseline_sbp),
        baseline_dbp:
          patientForm.baseline_dbp === ''
            ? null
            : Number(patientForm.baseline_dbp),
        baseline_bmi:
          patientForm.baseline_bmi === ''
            ? null
            : Number(patientForm.baseline_bmi),
        baseline_egfr:
          patientForm.baseline_egfr === ''
            ? null
            : Number(patientForm.baseline_egfr),
        baseline_hb:
          patientForm.baseline_hb === ''
            ? null
            : Number(patientForm.baseline_hb),
        raasi: !!patientForm.raasi,
        glp1ra: !!patientForm.glp1ra,
        sglt2i: !!patientForm.sglt2i,
        statin: !!patientForm.statin
      };

      let savedPatientId = patientForm.patient_id;
      if (patientForm.editing) {
        await request(
          `/patients/${encodeURIComponent(patientForm.patient_id)}`,
          { method: 'PUT', body: payload }
        );
      } else {
        const created = await request('/patients', {
          method: 'POST',
          body: payload
        });
        savedPatientId = created.patient_id;
      }

      await loadPatients();
      setSelectedId(savedPatientId);
      setModal('');
      notify('Patient saved to MySQL.');
    } catch (e) {
      notify(`Could not save patient: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function saveVisit(e) {
    e.preventDefault();

    // Enforce the date rule in JavaScript as well as in the date input.
    // This prevents manually typed or altered future dates from being submitted.
    const today = getLocalDateString();
    if (!visitForm.visit_date) {
      notify('Please select a visit date.');
      return;
    }
    if (visitForm.visit_date > today) {
      notify('Future visit dates are not allowed. Select today or an earlier date.');
      return;
    }

    try {
      await request(
        `/patients/${encodeURIComponent(visitForm.patient_id)}/visits`,
        {
          method: 'POST',
          body: {
            visit_date: visitForm.visit_date,
            encounter_type: visitForm.encounter_type || 'outpatient',
            labs: {
              // eGFR is calculated by the backend when it is not supplied.
              // ACR is intentionally not collected in this form.
              creatinine_mg_dl: Number(visitForm.creatinine),
              sbp_mmhg: Number(visitForm.sbp),
              dbp_mmhg: Number(visitForm.dbp),
              hemoglobin_g_dl: Number(visitForm.hb),
              potassium_mmol_l: Number(visitForm.potassium)
            }
          }
        }
      );

      await loadPatients();
      setModal('');
      notify('Visit and lab result saved.');
    } catch (e) {
      notify(`Could not save visit: ${e.message}`);
    }
  }

  async function removePatient(p) {
    if (
      !window.confirm(
        `Delete ${p.name} (${p.id}) and all linked visit/lab data? This cannot be undone.`
      )
    ) {
      return;
    }

    try {
      await request(`/patients/${encodeURIComponent(p.id)}`, {
        method: 'DELETE'
      });

      await loadPatients();
      notify('Patient deleted.');
    } catch (e) {
      notify(e.message);
    }
  }

  async function saveProfile(e) {
    e.preventDefault();
    setProfileBusy(true);

    try {
      const d = await request('/profile', {
        method: 'PUT',
        body: profile
      });

      setProfile({
        ...profile,
        full_name: d.full_name || profile.full_name,
        email: d.email || profile.email,
        hospital: d.hospital || profile.hospital
      });

      setUser({ ...user, ...d });
      notify('Profile saved.');
    } catch (e) {
      notify(e.message);
    } finally {
      setProfileBusy(false);
    }
  }

  async function markRead(n) {
    try {
      await request(`/notifications/${n.notification_id}/read`, {
        method: 'PATCH',
        body: {}
      });

      await loadNotifications();
    } catch (e) {
      notify(e.message);
    }
  }

  async function approve(u, status) {
    try {
      await request(`/admin/users/${u.user_id}/status`, {
        method: 'PATCH',
        body: { status }
      });

      await loadAdmin();
      notify(`Account ${status.toLowerCase()}.`);
    } catch (e) {
      notify(e.message);
    }
  }

  // Upload stores the file and metadata. It does not perform indexing.
  async function submitResource(e) {
    e.preventDefault();

    if (!resourceForm.file) {
      notify('Choose a PDF or text file first.');
      return;
    }

    const form = new FormData();

    Object.entries(resourceForm).forEach(([k, v]) => {
      if (k === 'file') {
        form.append('file', v);
      } else if (v !== '' && v != null) {
        form.append(k, v);
      }
    });

    try {
      await request('/resources', {
        method: 'POST',
        body: form,
        isForm: true
      });

      await loadResources();

      setResourceForm({
        title: '',
        category: 'Guidelines',
        source_name: '',
        source_url: '',
        version_label: '',
        file: null
      });

      notify('Resource uploaded. Click Index document when ready.');
    } catch (e) {
      notify(`Upload failed: ${e.message}`);
    }
  }

  async function exportPdf(patientId = null) {
    const qs = new URLSearchParams();

    if (reportFilter.risk !== 'All') {
      qs.set('risk', reportFilter.risk);
    }

    if (reportFilter.source !== 'All') {
      qs.set('source_code', reportFilter.source);
    }

    if (reportFilter.search) {
      qs.set('search', reportFilter.search);
    }

    if (reportFilter.period) {
      qs.set('period', reportFilter.period);
    }

    const path = patientId
      ? `/reports/patients/${encodeURIComponent(patientId)}/pdf`
      : `/reports/cohort/pdf?${qs.toString()}`;

    try {
      const blob = await request(path, { responseType: 'blob' });

      downloadBlob(
        blob,
        patientId ? `ckd-${patientId}-report.pdf` : 'ckd-cohort-report.pdf'
      );
    } catch (e) {
      notify(`PDF export failed: ${e.message}`);
    }
  }

  const nav = [
    ['Dashboard', LayoutDashboard],
    ['Patients', Users],
    ['Visits', CalendarDays],
    ['Risk Stratification', Activity],
    ['Reports', ClipboardList],
    ['Knowledge Base', BookOpen],
    ['Clinical Assistant', Activity]
  ];

  if (!user) {
    return (
      <Login
        onLogin={login}
        onRegister={register}
        loading={loading}
        error={error}
      />
    );
  }

  const high = patients.filter(p => normalizeRisk(p.risk) === 'High').length;
  const medium = patients.filter(p => normalizeRisk(p.risk) === 'Medium').length;
  const low = patients.filter(p => normalizeRisk(p.risk) === 'Low').length;

  return (
    <div className={`app theme-${theme}`}>
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">
            <HeartPulse size={23} />
          </span>
          <div>
            <strong>CKD Care</strong>
            <small>Clinical decision support</small>
          </div>
          <button
            className="icon-btn close-nav"
            onClick={() => setMobileNav(false)}
          >
            <X />
          </button>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        {nav.map(([label, I]) => (
          <button
            key={label}
            className={`nav-item ${page === label ? 'active' : ''}`}
            onClick={() => go(label)}
          >
            <I size={18} />
            <span>{label}</span>
            {label === 'Patients' && (
              <span className="nav-count">{patients.length}</span>
            )}
          </button>
        ))}

        {user.role === 'ADMIN' && (
          <button
            className={`nav-item ${page === 'Admin' ? 'active' : ''}`}
            onClick={() => go('Admin')}
          >
            <UserCheck size={18} />
            <span>Account approvals</span>
            {adminPending.length > 0 && (
              <span className="nav-count">{adminPending.length}</span>
            )}
          </button>
        )}

        <div className="sidebar-bottom">
          <div className="secure-note">
            <ShieldCheck size={17} />
            <div>
              <strong>Privacy first</strong>
              <small>Access depends on your approved role.</small>
            </div>
          </div>

          <button className="nav-item" onClick={() => go('Profile')}>
            <Settings size={18} />
            <span>Profile & Settings</span>
          </button>

          <button className="nav-item" onClick={signOut}>
            <LogOut size={18} />
            <span>Sign out</span>
          </button>

          <div className="sidebar-user">
            <div className="avatar">
              {initials(user.full_name || user.username)}
            </div>
            <div className="user-lines">
              <strong>{user.full_name || user.username}</strong>
              <small>{user.role}</small>
            </div>
          </div>
        </div>
      </aside>

      {mobileNav && (
        <div
          className="nav-overlay"
          onClick={() => setMobileNav(false)}
        />
      )}

      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-btn mobile-menu"
            onClick={() => setMobileNav(true)}
          >
            <Menu size={20} />
          </button>

          <div className="crumb">
            <span>CKD Care</span>
            <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>

          <div className="top-actions">
            <div className="global-search">
              <Search size={16} />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search patients, IDs..."
                onKeyDown={e => e.key === 'Enter' && go('Patients')}
              />
              <kbd>Ctrl K</kbd>
            </div>

            <div className="notification-wrap">
              <button
                className="icon-btn notification-btn"
                onClick={() => {
                  setShowNotifications(v => !v);
                  if (!showNotifications) loadNotifications();
                }}
                title="Notifications"
              >
                <Bell size={18} />
                {notifications.some(n => !n.is_read) && <i />}
              </button>

              {showNotifications && (
                <div className="notification-popover">
                  <div className="popover-title">
                    Notifications
                    <button
                      className="icon-btn"
                      onClick={() => setShowNotifications(false)}
                    >
                      <X size={15} />
                    </button>
                  </div>

                  {notifications.length ? (
                    notifications.map(n => (
                      <button
                        key={n.notification_id}
                        className={`notification-row ${n.is_read ? '' : 'unread'}`}
                        onClick={() => {
                          markRead(n);
                          if (n.patient_id) {
                            setSelectedId(n.patient_id);
                            go('Patient Profile');
                          }
                        }}
                      >
                        <b>{n.title}</b>
                        <small>{n.message}</small>
                        <time>{new Date(n.created_at).toLocaleString()}</time>
                      </button>
                    ))
                  ) : (
                    <p className="empty-state">No notifications.</p>
                  )}
                </div>
              )}
            </div>

            <button className="top-user" onClick={() => go('Profile')}>
              <span className="avatar small">
                {initials(user.full_name || user.username)}
              </span>
              <span>
                <strong>{user.full_name || user.username}</strong>
                <small>{user.role}</small>
              </span>
              <ChevronDown size={15} />
            </button>

            <button
              className="icon-btn"
              title="Toggle theme"
              onClick={() =>
                persistTheme(theme === 'light' ? 'dark' : 'light')
              }
            >
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
        </header>

        <div className="page-content">
          {page === 'Dashboard' && (
            <>
              <PageTitle
                eyebrow="CLINICAL OVERVIEW"
                title={`Welcome, ${user.full_name || user.username}`}
                subtitle="Live summary from your MySQL-backed patient records."
                actions={
                  <>
                    <Button onClick={() => go('Reports')}>
                      <FileText size={15} /> Reports
                    </Button>
                    <Button
                      kind="primary"
                      onClick={() => {
                        setPatientForm({
                          patient_id: '',
                          full_name: '',
                          source_code: 'HOSP',
                          source_patient_id: '',
                          age_at_baseline: '',
                          gender: '',
                          baseline_egfr: '',
                          baseline_sbp: '',
                          baseline_dbp: '',
                          baseline_bmi: '',
                          baseline_hb: '',
                          diabetes: false,
                          hypertension: false,
                          cvd: false,
                          ihd: false,
                          dyslipidemia: false,
                          raasi: false,
                          sglt2i: false,
                          glp1ra: false,
                          statin: false,
                          editing: false
                        });
                        setModal('patient');
                      }}
                    >
                      <Plus size={16} /> Add patient
                    </Button>
                  </>
                }
              />

              <div className="stats-grid">
                <div className="stat-card">
                  <span>Total patients</span>
                  <strong>{patients.length}</strong>
                  <small>Loaded from MySQL</small>
                </div>
                <div className="stat-card">
                  <span>High risk</span>
                  <strong>{high}</strong>
                  <small>Saved analysis only</small>
                </div>
                <div className="stat-card">
                  <span>Medium risk</span>
                  <strong>{medium}</strong>
                  <small>Saved analysis only</small>
                </div>
                <div className="stat-card">
                  <span>Low risk</span>
                  <strong>{low}</strong>
                  <small>Saved analysis only</small>
                </div>
              </div>

              <div className="dashboard-grid">
                <Panel
                  title="Latest eGFR trend"
                  subtitle="Observed visit measurements, not model output"
                >
                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={patients
                          .slice(0, 8)
                          .filter(p => p.egfr != null)
                          .map(p => ({ patient: p.id, egfr: p.egfr }))}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="patient" />
                        <YAxis />
                        <Tooltip />
                        <Area
                          type="monotone"
                          dataKey="egfr"
                          stroke="#3987ed"
                          fill="#3987ed"
                          fillOpacity={0.12}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Panel>

                <Panel
                  title="Risk distribution"
                  subtitle="Only saved model results are counted"
                >
                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={[
                          { name: 'High', value: high },
                          { name: 'Medium', value: medium },
                          { name: 'Low', value: low }
                        ]}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                          {['High', 'Medium', 'Low'].map(n => (
                            <Cell key={n} fill={riskColors[n]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Panel>
              </div>

              <Panel
                title="Patient overview"
                subtitle={`${allFiltered.length} matching records`}
              >
                <div className="list-toolbar">
                  <input
                    placeholder="Search name or patient ID"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                  />
                  <select
                    value={riskFilter}
                    onChange={e => setRiskFilter(e.target.value)}
                  >
                    <option>All</option>
                    <option>High</option>
                    <option>Medium</option>
                    <option>Low</option>
                    <option>Unassessed</option>
                  </select>
                  <select value={sort} onChange={e => setSort(e.target.value)}>
                    <option value="Recent">Patient ID</option>
                    <option value="Name">Name</option>
                    <option value="Risk">Risk</option>
                  </select>
                </div>

                <PatientTable
                  rows={allFiltered.slice(0, 10)}
                  open={id => {
                    setSelectedId(id);
                    go('Patient Profile');
                  }}
                  edit={p => {
                    setPatientForm({
                      ...p,
                      patient_id: p.id,
                      full_name: p.name,
                      age_at_baseline: p.age,
                      source_code: p.source,
                      source_patient_id: p.source_patient_id,
                      editing: true
                    });
                    setModal('patient');
                  }}
                  remove={removePatient}
                />
              </Panel>
            </>
          )}

          {page === 'Patients' && (
            <>
              <PageTitle
                eyebrow="PATIENT MANAGEMENT"
                title="Patients"
                subtitle="Patient and laboratory records are read from MySQL."
                actions={
                  <Button
                    kind="primary"
                    onClick={() => {
                      setPatientForm({
                        patient_id: '',
                        full_name: '',
                        source_code: 'HOSP',
                        source_patient_id: '',
                        age_at_baseline: '',
                        gender: '',
                        baseline_egfr: '',
                        baseline_sbp: '',
                        baseline_dbp: '',
                        baseline_bmi: '',
                        baseline_hb: '',
                        diabetes: false,
                        hypertension: false,
                        cvd: false,
                        ihd: false,
                        dyslipidemia: false,
                        raasi: false,
                        sglt2i: false,
                        glp1ra: false,
                        statin: false,
                        editing: false
                      });
                      setModal('patient');
                    }}
                  >
                    <Plus size={16} /> Add patient
                  </Button>
                }
              />

              <Panel
                title="Patient records"
                subtitle="Search, filter, view and manage authorized records"
              >
                <div className="list-toolbar">
                  <input
                    placeholder="Search name or patient ID"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                  />

                  <label>
                    <Filter size={14} />
                    <select
                      value={riskFilter}
                      onChange={e => setRiskFilter(e.target.value)}
                    >
                      <option>All</option>
                      <option>High</option>
                      <option>Medium</option>
                      <option>Low</option>
                      <option>Unassessed</option>
                    </select>
                  </label>

                  <select value={sort} onChange={e => setSort(e.target.value)}>
                    <option value="Recent">Patient ID</option>
                    <option value="Name">Name</option>
                    <option value="Risk">Risk</option>
                  </select>
                </div>

                <PatientTable
                  rows={allFiltered}
                  open={id => {
                    setSelectedId(id);
                    go('Patient Profile');
                  }}
                  edit={p => {
                    setPatientForm({
                      ...p,
                      patient_id: p.id,
                      full_name: p.name,
                      age_at_baseline: p.age,
                      source_code: p.source,
                      source_patient_id: p.source_patient_id,
                      editing: true
                    });
                    setModal('patient');
                  }}
                  remove={removePatient}
                />
              </Panel>
            </>
          )}

          {page === 'Patient Profile' && selected && (
            <>
              <button className="back-link" onClick={() => go('Patients')}>
                <ChevronLeft size={16} /> Back to patients
              </button>

              <div className="profile-hero">
                <div className="profile-person">
                  <div className="profile-avatar">
                    {initials(selected.name)}
                  </div>
                  <div>
                    <div className="eyebrow">
                      PATIENT PROFILE · {selected.id}
                    </div>
                    <h1>{selected.name}</h1>
                    <p>
                      {selected.age ?? '—'} years · {selected.gender} ·{' '}
                      {selected.source}
                    </p>
                  </div>
                </div>

                <div className="profile-actions">
                  <Tag>{selected.risk}</Tag>
                  {(user?.role === 'DOCTOR' || user?.role === 'ADMIN') && (
                    <Button kind="primary" onClick={() => assessPatient(selected.id)} disabled={loading}>
                      <Activity size={15} /> {loading ? 'Assessing…' : 'Assess patient'}
                    </Button>
                  )}
                  <Button onClick={() => exportPdf(selected.id)}>
                    <Download size={15} /> Patient PDF
                  </Button>
                  <Button
                    kind="primary"
                    onClick={() => {
                      setVisitForm({
                        patient_id: selected.id,
                        visit_date: getLocalDateString(),
                        encounter_type: 'outpatient',
                        egfr: '',
                        creatinine: '',
                        acr: '',
                        sbp: '',
                        dbp: '',
                        hb: '',
                        potassium: ''
                      });
                      setModal('visit');
                    }}
                  >
                    <Plus size={15} /> Add visit
                  </Button>
                </div>
              </div>

              <div className="profile-grid">
                <Panel title="Baseline / demographic information">
                  <dl className="detail-list">
                    {[
                      ['Patient ID', selected.id],
                      ['Name', selected.name],
                      ['Age', selected.age ?? '—'],
                      ['Gender', selected.gender],
                      ['Data source', selected.source],
                      ['eGFR', selected.egfr ?? '—'],
                      ['ACR mg/g', selected.acr ?? '—'],
                      ['Creatinine mg/dL', selected.creatinine ?? '—'],
                      ['Blood pressure', selected.bp],
                      ['Diabetes', selected.diabetes ? 'Yes' : 'No'],
                      ['Hypertension', selected.hypertension ? 'Yes' : 'No']
                    ].map(([a, b]) => (
                      <React.Fragment key={a}>
                        <dt>{a}</dt>
                        <dd>{b}</dd>
                      </React.Fragment>
                    ))}
                  </dl>
                </Panel>

                <Panel
                  title="eGFR trend"
                  subtitle="Dated values in the patient's database visit history"
                >
                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={[...selected.visits]
                          .reverse()
                          .filter(v => v.egfr != null)}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Line
                          dataKey="egfr"
                          stroke="#3987ed"
                          strokeWidth={2.5}
                          dot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Panel>
              </div>

              <Panel
                title="Visit history"
                subtitle="All recorded encounters and linked labs"
              >
                <VisitTable visits={selected.visits} />
              </Panel>

              <div className="report-note">
                <AlertCircle size={15} />
                This application is a student clinical decision-support
                prototype; not a substitute for clinical judgement.
              </div>
            </>
          )}

          {page === 'Visits' && (
            <>
              <PageTitle
                eyebrow="LONGITUDINAL RECORDS"
                title="Visits & lab history"
                subtitle="Records are loaded from the relational database."
              />

              <Panel title="Patient visit history">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Patient</th>
                        <th>Date</th>
                        <th>eGFR</th>
                        <th>ACR</th>
                        <th>Creatinine</th>
                        <th>Blood pressure</th>
                      </tr>
                    </thead>
                    <tbody>
                      {patients.flatMap(p =>
                        p.visits.map((v, i) => (
                          <tr key={`${p.id}-${v.date}-${i}`}>
                            <td>{p.name} ({p.id})</td>
                            <td>{v.date || '—'}</td>
                            <td>{v.egfr ?? '—'}</td>
                            <td>{v.acr ?? '—'}</td>
                            <td>{v.creatinine ?? '—'}</td>
                            <td>{v.bp}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </>
          )}

          {page === 'Risk Stratification' && (
            <>
              <PageTitle
                eyebrow="AI-ASSISTED REVIEW"
                title="Risk stratification"
                subtitle="Only real saved model output is shown; unassessed records remain unassessed."
              />

              <Panel title="Saved progression-analysis results">
                <PatientTable
                  rows={allFiltered.filter(p => normalizeRisk(p.risk) !== 'Unassessed')}
                  open={id => {
                    setSelectedId(id);
                    go('Patient Profile');
                  }}
                  edit={p => {
                    setPatientForm({
                      ...p,
                      patient_id: p.id,
                      full_name: p.name,
                      age_at_baseline: p.age,
                      source_code: p.source,
                      source_patient_id: p.source_patient_id,
                      editing: true
                    });
                    setModal('patient');
                  }}
                  remove={removePatient}
                />

                {!allFiltered.some(p => normalizeRisk(p.risk) !== 'Unassessed') && (
                  <p className="empty-state">
                    No saved predictions yet. The model file is not included
                    in this package; analysis is intentionally not fabricated.
                  </p>
                )}
              </Panel>
            </>
          )}

          {page === 'Reports' && (
            <>
              <PageTitle
                eyebrow="CLINICAL ANALYTICS"
                title="Reports & analytics"
                subtitle="PDF files are generated by the backend from the selected MySQL cohort."
                actions={
                  <Button kind="primary" onClick={() => exportPdf()}>
                    <Download size={16} /> Export cohort PDF
                  </Button>
                }
              />

              <div className="report-toolbar">
                <div className="segmented">
                  {['eGFR Trends', 'Risk Distribution', 'Patient Cohort'].map(t => (
                    <button
                      className={reportTab === t ? 'active' : ''}
                      key={t}
                      onClick={() => setReportTab(t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>

                <div className="report-filters">
                  <label>
                    Risk
                    <select
                      value={reportFilter.risk}
                      onChange={e =>
                        setReportFilter(current => ({ ...current, risk: e.target.value }))
                      }
                    >
                      <option>All</option>
                      <option>High</option>
                      <option>Medium</option>
                      <option>Low</option>
                      <option>Unassessed</option>
                    </select>
                  </label>

                  <label>
                    Source
                    <select
                      value={reportFilter.source}
                      onChange={e =>
                        setReportFilter(current => ({ ...current, source: e.target.value }))
                      }
                    >
                      <option>All</option>
                      {[...new Set(patients.map(p => p.source))]
                        .filter(Boolean)
                        .map(s => <option key={s}>{s}</option>)}
                    </select>
                  </label>

                  <label>
                    Period
                    <select
                      value={reportFilter.period}
                      onChange={e =>
                        setReportFilter(current => ({ ...current, period: e.target.value }))
                      }
                    >
                      <option>Last month</option>
                      <option>3 months</option>
                      <option>6 months</option>
                      <option>12 months</option>
                      <option>All</option>
                    </select>
                  </label>

                  <label>
                    Search
                    <input
                      value={reportFilter.search}
                      onChange={e =>
                        setReportFilter(current => ({ ...current, search: e.target.value }))
                      }
                      placeholder="Name or ID"
                    />
                  </label>
                </div>
              </div>

              <div className="report-stats">
                <div className="stat-card">
                  <span>Visible patients</span>
                  <strong>{reportFilteredPatients.length}</strong>
                  <small>Reports-filtered cohort</small>
                </div>
                <div className="stat-card">
                  <span>Mean current eGFR</span>
                  <strong>
                    {reportMeanEgfr}
                  </strong>
                  <small>Available measurements only</small>
                </div>
                <div className="stat-card">
                  <span>ACR ≥ 300 mg/g</span>
                  <strong>
                    {reportHighAcrCount}
                  </strong>
                  <small>Latest measurement</small>
                </div>
                <div className="stat-card">
                  <span>With visit history</span>
                  <strong>
                    {reportPatientsWithVisits}
                  </strong>
                  <small>Relational visit records</small>
                </div>
              </div>

              <div className="report-grid">
                <Panel title={reportTab} subtitle="Preview chart from loaded MySQL records">
                  <div className="report-chart">
                    {reportTab === 'Risk Distribution' ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={[
                            { name: 'High', value: reportRiskCounts.High },
                            { name: 'Medium', value: reportRiskCounts.Medium },
                            { name: 'Low', value: reportRiskCounts.Low },
                            { name: 'Unassessed', value: reportRiskCounts.Unassessed }
                          ]}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis allowDecimals={false} />
                          <Tooltip />
                          <Bar dataKey="value">
                            {['High', 'Medium', 'Low', 'Unassessed'].map(n => (
                              <Cell key={n} fill={riskColors[n] || '#94a3b8'} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : reportTab === 'Patient Cohort' ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={[
                            { name: 'Diabetes', value: reportFilteredPatients.filter(p => p.diabetes).length },
                            { name: 'Hypertension', value: reportFilteredPatients.filter(p => p.hypertension).length },
                            { name: 'IHD', value: reportFilteredPatients.filter(p => p.ihd).length },
                            { name: 'CVD', value: reportFilteredPatients.filter(p => p.cvd).length }
                          ]}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="name" />
                          <YAxis allowDecimals={false} />
                          <Tooltip />
                          <Bar dataKey="value" fill="#3987ed" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={reportVisits
                            .filter(visit => visit.egfr != null && Number.isFinite(Number(visit.egfr)) && isValidDate(visit.date))
                            .map(visit => ({ date: visit.date, patient: visit.patientId, egfr: Number(visit.egfr) }))
                            .sort((a, b) => String(a.date).localeCompare(String(b.date)))
                            .slice(-150)}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" hide />
                          <YAxis />
                          <Tooltip />
                          <Line
                            type="monotone"
                            dataKey="egfr"
                            stroke="#3987ed"
                            dot={{ r: 2 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>

                  <div className="report-note">
                    <AlertCircle size={15} />
                    Browser preview uses loaded records and visit dates; the backend remains
                    authoritative for PDF generation and its period semantics.
                  </div>
                </Panel>

                <Panel
                  title="Cohort counts"
                  subtitle="Reflects current patient list and risk result availability"
                >
                  <div className="report-risk-list">
                    {[
                      ['High', reportRiskCounts.High],
                      ['Medium', reportRiskCounts.Medium],
                      ['Low', reportRiskCounts.Low],
                      ['Unassessed', reportRiskCounts.Unassessed]
                    ].map(([n, v]) => (
                      <div key={n}>
                        <span>
                          <i style={{ background: riskColors[n] || '#94a3b8' }} />
                          {n}
                        </span>
                        <strong>{v}</strong>
                        <small>
                          {reportFilteredPatients.length ? Math.round((v / reportFilteredPatients.length) * 100) : 0}%
                        </small>
                      </div>
                    ))}
                  </div>

                  <Button kind="primary" onClick={() => exportPdf()}>
                    <Download size={15} /> Download same cohort as PDF
                  </Button>
                </Panel>
              </div>

              <Panel
                title="Included patients"
                subtitle="Server report filters are applied when exporting"
              >
                <PatientTable
                  rows={reportFilteredPatients}
                  open={id => {
                    setSelectedId(id);
                    go('Patient Profile');
                  }}
                  edit={() => {}}
                  remove={() => {}}
                />
              </Panel>
            </>
          )}

          {page === 'Knowledge Base' && (
            <>
              <PageTitle
                eyebrow="KNOWLEDGE RESOURCES"
                title="Knowledge base"
                subtitle="Upload resources and index documents to make their content available to the Clinical Assistant."
                actions={
                  <Button
                    kind="primary"
                    onClick={() => go('Knowledge Base')}
                  >
                    <Plus size={16} /> Add resource
                  </Button>
                }
              />

              <div className="knowledge-layout">
                <aside className="panel knowledge-nav">
                  <strong>Resource categories</strong>
                  <p>
                    Guidelines · Drug information · Patient education · Other
                  </p>
                  <p className="muted-note">
                    Uploaded documents can be indexed to generate embeddings and used by the
                    Clinical Assistant.
                  </p>
                </aside>

                <div className="panel knowledge-content">
                  <form onSubmit={submitResource} className="resource-form">
                    <div className="panel-heading">
                      <div>
                        <h3>Add resource</h3>
                        <p>PDF and plain-text documents only.</p>
                      </div>
                    </div>

                    <div className="form-grid">
                      <label>
                        Title *
                        <input
                          required
                          value={resourceForm.title}
                          onChange={e =>
                            setResourceForm({
                              ...resourceForm,
                              title: e.target.value
                            })
                          }
                        />
                      </label>

                      <label>
                        Category *
                        <select
                          value={resourceForm.category}
                          onChange={e =>
                            setResourceForm({
                              ...resourceForm,
                              category: e.target.value
                            })
                          }
                        >
                          <option>Guidelines</option>
                          <option>Drug Information</option>
                          <option>Patient Education</option>
                          <option>Other</option>
                        </select>
                      </label>

                      <label>
                        Source name
                        <input
                          value={resourceForm.source_name}
                          onChange={e =>
                            setResourceForm({
                              ...resourceForm,
                              source_name: e.target.value
                            })
                          }
                        />
                      </label>

                      <label>
                        Version / date
                        <input
                          value={resourceForm.version_label}
                          onChange={e =>
                            setResourceForm({
                              ...resourceForm,
                              version_label: e.target.value
                            })
                          }
                        />
                      </label>

                      <label className="span-two">
                        Source URL
                        <input
                          type="url"
                          value={resourceForm.source_url}
                          onChange={e =>
                            setResourceForm({
                              ...resourceForm,
                              source_url: e.target.value
                            })
                          }
                        />
                      </label>

                      <label className="span-two">
                        Choose PDF/TXT file *
                        <input
                          type="file"
                          accept="application/pdf,text/plain,.pdf,.txt"
                          required
                          onChange={e =>
                            setResourceForm({
                              ...resourceForm,
                              file: e.target.files?.[0] || null
                            })
                          }
                        />
                      </label>
                    </div>

                    <Button kind="primary" type="submit">
                      <Upload size={16} /> Upload resource
                    </Button>
                  </form>

                  <div className="knowledge-list">
                    <div className="panel-heading">
                      <div>
                        <h3>Uploaded resources</h3>
                        <p>{resources.length} files registered in MySQL</p>
                      </div>
                      <Button onClick={loadResources}>Refresh</Button>
                    </div>

                    {resources.map(r => (
                      <div className="knowledge-card" key={r.resource_id}>
                        <FileText size={22} />

                        <div className="knowledge-card-main">
                          <div className="knowledge-title-row">
                            <h4>{r.title}</h4>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <Tag>{r.status}</Tag>
                              <Button
                                onClick={() => indexResource(r.resource_id)}
                                disabled={r.status === 'PROCESSING'}
                              >
                                {r.status === 'INDEXED' ? 'Re-index' : 'Index'}
                              </Button>
                            </div>
                          </div>

                          <p>
                            {r.category} · {r.source_name || 'Source not specified'}
                          </p>

                          <small>
                            {r.original_filename} ·{' '}
                            {(r.file_size_bytes / 1024).toFixed(1)} KB ·{' '}
                            {new Date(r.created_at).toLocaleString()}
                          </small>

                        </div>
                      </div>
                    ))}

                    {!resources.length && (
                      <p className="empty-state">
                        No uploaded resources yet.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}

          {page === 'Clinical Assistant' && (
            <ClinicalAssistant
              selectedPatient={selected ? { id: selected.id, name: selected.name } : null}
            />
          )}

          {page === 'Profile' && (
            <>
              <PageTitle
                eyebrow="ACCOUNT PREFERENCES"
                title="Profile & settings"
                subtitle="Profile values are saved to the authenticated account."
              />

              <div className="settings-layout">
                <aside className="panel settings-nav">
                  <div className="settings-avatar">
                    <div className="profile-avatar">
                      {initials(user.full_name || user.username)}
                    </div>
                    <div>
                      <b>{user.full_name || user.username}</b>
                      <small>
                        {user.role} · {user.account_status}
                      </small>
                    </div>
                  </div>

                  <button className="nav-item active">
                    <Users size={17} /> My Profile
                  </button>

                  <button
                    className="nav-item"
                    onClick={() =>
                      persistTheme(theme === 'light' ? 'dark' : 'light')
                    }
                  >
                    {theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}
                    Theme & Appearance
                  </button>
                </aside>

                <form
                  className="panel settings-content"
                  onSubmit={saveProfile}
                >
                  <div className="panel-heading">
                    <div>
                      <h3>Profile information</h3>
                      <p>Role is controlled by Admin and cannot be changed here.</p>
                    </div>
                  </div>

                  <div className="form-grid">
                    <label>
                      Full name
                      <input
                        required
                        value={profile.full_name}
                        onChange={e =>
                          setProfile({ ...profile, full_name: e.target.value })
                        }
                      />
                    </label>

                    <label>
                      Email address
                      <input
                        required
                        type="email"
                        value={profile.email}
                        onChange={e =>
                          setProfile({ ...profile, email: e.target.value })
                        }
                      />
                    </label>

                    <label className="span-two">
                      Hospital / organisation (profile field)
                      <input
                        value={profile.hospital}
                        onChange={e =>
                          setProfile({ ...profile, hospital: e.target.value })
                        }
                        placeholder="Optional"
                      />
                    </label>
                  </div>

                  <Button
                    kind="primary"
                    type="submit"
                    disabled={profileBusy}
                  >
                    Save profile
                  </Button>

                  <p className="muted-note">
                    If your schema doesn't contain a hospital column, the API
                    safely returns an empty hospital field and stores no
                    unsupported column.
                  </p>
                </form>
              </div>
            </>
          )}

          {page === 'Admin' && user.role === 'ADMIN' && (
            <>
              <PageTitle
                eyebrow="ACCOUNT MANAGEMENT"
                title="Pending account approvals"
                subtitle="Only ADMIN users may approve or reject accounts."
              />

              <Panel title="Awaiting approval">
                {adminPending.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Account</th>
                          <th>Email</th>
                          <th>Requested role</th>
                          <th>Created</th>
                          <th>Actions</th>
                        </tr>
                      </thead>

                      <tbody>
                        {adminPending.map(u => (
                          <tr key={u.user_id}>
                            <td>
                              {u.full_name || u.username}
                              <small>{u.username}</small>
                            </td>
                            <td>{u.email}</td>
                            <td>{u.role}</td>
                            <td>
                              {u.created_at
                                ? new Date(u.created_at).toLocaleDateString()
                                : '—'}
                            </td>
                            <td>
                              <Button
                                kind="primary"
                                onClick={() => approve(u, 'APPROVED')}
                              >
                                Approve
                              </Button>{' '}
                              <Button onClick={() => approve(u, 'REJECTED')}>
                                Reject
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="empty-state">No pending users.</p>
                )}
              </Panel>
            </>
          )}
        </div>

        <footer className="footer">
          <span>CKD Care · Clinical Decision Support System</span>
          <span>
            {patients.length} patients · Authenticated MySQL connection
          </span>
        </footer>
      </main>

      {modal === 'patient' && (
        <Modal
          title={patientForm.editing ? 'Edit patient' : 'Add patient'}
          close={() => setModal('')}
        >
          <form onSubmit={savePatient}>
            <div className="form-grid">
              {patientForm.editing ? (
                <label>
                  Patient ID
                  <input value={patientForm.patient_id || ''} disabled />
                </label>
              ) : null}

              <label>
                Full name *
                <input
                  value={patientForm.full_name || ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      full_name: e.target.value
                    })
                  }
                  required
                />
              </label>

              <label>
                Source code
                <input
                  value={patientForm.source_code || ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      source_code: e.target.value
                    })
                  }
                  required
                  maxLength={10}
                />
              </label>

              {patientForm.editing && (
                <label>
                  Source patient ID
                  <input value={patientForm.source_patient_id || ''} disabled />
                </label>
              )}

              <label>
                Age at baseline
                <input
                  type="number"
                  min="0"
                  max="120"
                  step="any"
                  value={patientForm.age_at_baseline ?? ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      age_at_baseline: e.target.value
                    })
                  }
                />
              </label>

              <label>
                Gender
                <select
                  value={patientForm.gender ?? ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      gender: e.target.value
                    })
                  }
                >
                  <option value="">Not specified</option>
                  <option value="1">Male (1)</option>
                  <option value="2">Female (2)</option>
                  <option value="3">Other (3)</option>
                </select>
              </label>

              <label>
                Baseline eGFR
                <input
                  type="number"
                  min="0"
                  max="250"
                  step="any"
                  value={patientForm.baseline_egfr ?? ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      baseline_egfr: e.target.value
                    })
                  }
                />
              </label>

              <label>
                Baseline systolic BP
                <input
                  type="number"
                  value={patientForm.baseline_sbp ?? ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      baseline_sbp: e.target.value
                    })
                  }
                />
              </label>

              <label>
                Baseline diastolic BP
                <input
                  type="number"
                  value={patientForm.baseline_dbp ?? ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      baseline_dbp: e.target.value
                    })
                  }
                />
              </label>

              <label>
                BMI
                <input
                  type="number"
                  step="any"
                  value={patientForm.baseline_bmi ?? ''}
                  onChange={e =>
                    setPatientForm({
                      ...patientForm,
                      baseline_bmi: e.target.value
                    })
                  }
                />
              </label>

              {[
                ['diabetes', 'Diabetes'],
                ['hypertension', 'Hypertension'],
                ['ihd', 'IHD'],
                ['cvd', 'CVD'],
                ['dyslipidemia', 'Dyslipidemia'],
                ['raasi', 'RAASi'],
                ['glp1ra', 'GLP-1 RA'],
                ['sglt2i', 'SGLT2i'],
                ['statin', 'Statin']
              ].map(([k, l]) => (
                <label className="check-label" key={k}>
                  <input
                    type="checkbox"
                    checked={!!patientForm[k]}
                    onChange={e =>
                      setPatientForm({
                        ...patientForm,
                        [k]: e.target.checked
                      })
                    }
                  />
                  {l}
                </label>
              ))}
            </div>

            <div className="modal-footer">
              <Button onClick={() => setModal('')} type="button">
                Cancel
              </Button>
              <Button kind="primary" type="submit" disabled={loading}>
                Save
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {modal === 'visit' && (
        <Modal
          title="Add visit and lab result"
          close={() => setModal('')}
        >
          <form onSubmit={saveVisit}>
            <div className="form-grid">
              <label>
                Patient
                <input value={visitForm.patient_id} disabled />
              </label>

              <label>
                Visit date *
                <input
                  type="date"
                  required
                  max={getLocalDateString()}
                  value={visitForm.visit_date}
                  onChange={e =>
                    setVisitForm({
                      ...visitForm,
                      visit_date: e.target.value
                    })
                  }
                />
              </label>

              <label>
                Creatinine (mg/dL) *
                <input
                  type="number"
                  min="0.01"
                  step="any"
                  required
                  value={visitForm.creatinine}
                  onChange={e =>
                    setVisitForm({
                      ...visitForm,
                      creatinine: e.target.value
                    })
                  }
                />
              </label>

              <label>
                Systolic BP *
                <input
                  type="number"
                  min="1"
                  step="any"
                  required
                  value={visitForm.sbp}
                  onChange={e =>
                    setVisitForm({ ...visitForm, sbp: e.target.value })
                  }
                />
              </label>

              <label>
                Diastolic BP *
                <input
                  type="number"
                  min="1"
                  step="any"
                  required
                  value={visitForm.dbp}
                  onChange={e =>
                    setVisitForm({ ...visitForm, dbp: e.target.value })
                  }
                />
              </label>

              <label>
                Haemoglobin *
                <input
                  type="number"
                  min="0.1"
                  step="any"
                  required
                  value={visitForm.hb}
                  onChange={e =>
                    setVisitForm({ ...visitForm, hb: e.target.value })
                  }
                />
              </label>

              <label>
                Potassium *
                <input
                  type="number"
                  min="0.1"
                  step="any"
                  required
                  value={visitForm.potassium}
                  onChange={e =>
                    setVisitForm({
                      ...visitForm,
                      potassium: e.target.value
                    })
                  }
                />
              </label>
            </div>

            <div className="modal-footer">
              <Button type="button" onClick={() => setModal('')}>
                Cancel
              </Button>
              <Button kind="primary" type="submit">
                Save visit
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {toast && (
        <div className="toast">
          <Check size={16} />
          {toast}
        </div>
      )}
    </div>
  );
}

function PatientTable({rows,open,edit,remove}){return <div className="table-scroll"><table><thead><tr><th>Patient</th><th>Age / gender</th><th>Source</th><th>eGFR</th><th>ACR</th><th>Progression result</th><th>Actions</th></tr></thead><tbody>{rows.map(p=><tr key={p.id}><td><button className="patient-name" onClick={()=>open(p.id)}><span className="patient-avatar">{initials(p.name)}</span><span><b>{p.name}</b><small>{p.id}</small></span></button></td><td>{p.age??'—'} / {p.gender}</td><td>{p.source}</td><td>{p.egfr??'—'}</td><td>{p.acr??'—'}</td><td><Tag>{p.risk}</Tag></td><td><div className="actions-cell"><button className="table-link" onClick={()=>open(p.id)}>View</button>{edit&&<button className="table-link" onClick={()=>edit(p)}>Edit</button>}{remove&&<button className="table-link danger-text" onClick={()=>remove(p)}>Delete</button>}</div></td></tr>)}</tbody></table>{!rows.length&&<p className="empty-state">No patient records found in MySQL. Add a patient or import your research cohort.</p>}</div>}
function VisitTable({visits}){return <div className="table-scroll"><table><thead><tr><th>Date</th><th>eGFR</th><th>ACR</th><th>Creatinine</th><th>BP</th><th>Hb</th><th>K</th></tr></thead><tbody>{visits.map((v,i)=><tr key={`${v.date}-${i}`}><td>{v.date||'—'}</td><td>{v.egfr??'—'}</td><td>{v.acr??'—'}</td><td>{v.creatinine??'—'}</td><td>{v.bp}</td><td>{v.hb??'—'}</td><td>{v.potassium??'—'}</td></tr>)}</tbody></table>{!visits.length&&<p className="empty-state">No visit/lab records for this patient.</p>}</div>}
function Modal({title,close,children}){return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&close()}><div className="modal"><div className="modal-header"><h2>{title}</h2><button className="icon-btn" onClick={close}><X/></button></div><div className="modal-body">{children}</div></div></div>}
export default App;
