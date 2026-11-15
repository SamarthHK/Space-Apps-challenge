import './style.css';
import './workspace.css';
import { startWorkspace } from './views/workspace.js';

startWorkspace(import.meta.env.VITE_API_BASE_URL);
