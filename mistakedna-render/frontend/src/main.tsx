import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import Lab from './lab';
import curriculum from '../lib/curriculum.json';
import './styles.css';
createRoot(document.getElementById('root')!).render(<StrictMode><Lab curriculum={curriculum}/></StrictMode>);
