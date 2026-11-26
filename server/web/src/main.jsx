import '@mantine/core/styles.css';
import '@mantine/dropzone/styles.css';
import '@mantine/notifications/styles.css';
import { createRoot } from 'react-dom/client';
import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import App from './App.jsx';

const theme = createTheme({ primaryColor: 'indigo', defaultRadius: 'md', fontFamily: 'Inter, system-ui, sans-serif' });

createRoot(document.getElementById('root')).render(
  <MantineProvider theme={theme} defaultColorScheme="auto">
    <Notifications position="top-right" />
    <App />
  </MantineProvider>,
);
