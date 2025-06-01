import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Box, Container, Paper, Fab, useScrollTrigger, Zoom, Snackbar, Alert } from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import Navbar from './Navbar';

// ScrollToTop button component
function ScrollTop() {
  const trigger = useScrollTrigger({
    disableHysteresis: true,
    threshold: 100,
  });

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  };

  return (
    <Zoom in={trigger}>
      <Box
        onClick={scrollToTop}
        role="presentation"
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: 9999,
        }}
      >
        <Fab
          color="primary"
          size="medium"
          aria-label="scroll back to top"
          sx={{
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)',
            '&:hover': {
              transform: 'translateY(-4px)',
              boxShadow: '0 8px 16px rgba(0, 0, 0, 0.3)',
            },
            transition: 'all 0.3s',
          }}
        >
          <KeyboardArrowUpIcon />
        </Fab>
      </Box>
    </Zoom>
  );
}

// Main Layout component
function Layout() {
  // Global notification state
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });

  // Page transition variant for framer-motion
  const pageVariants = {
    initial: {
      opacity: 0,
      y: 10,
    },
    animate: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.4,
        ease: 'easeInOut',
      },
    },
    exit: {
      opacity: 0,
      y: -10,
      transition: {
        duration: 0.3,
        ease: 'easeInOut',
      },
    },
  };

  // Set up notification handler that can be used by child components
  useEffect(() => {
    // Create a global notification function
    window.showNotification = (message, severity = 'info') => {
      setNotification({ open: true, message, severity });
    };

    // Cleanup
    return () => {
      delete window.showNotification;
    };
  }, []);

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', width: '100%' }}>
      {/* Navigation */}
      <Navbar />

      {/* Main Content */}
      <Container 
        component="main" 
        maxWidth="xl" 
        sx={{ 
          flexGrow: 1, 
          py: 4, 
          px: { xs: 2, sm: 3, md: 4 },
          width: '100%'
        }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageVariants}
            style={{ width: '100%' }}
          >
            <Paper
              elevation={0}
              sx={{
                p: { xs: 2, md: 3 },
                borderRadius: 3,
                backgroundColor: 'transparent',
                width: '100%'
              }}
            >
              <Outlet />
            </Paper>
          </motion.div>
        </AnimatePresence>
      </Container>

      {/* Footer */}
      <Box
        component="footer"
        sx={{
          py: 3,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) => theme.palette.grey[100],
          borderTop: (theme) => `1px solid ${theme.palette.grey[200]}`,
          width: '100%'
        }}
      >
        <Container maxWidth="xl">
          <Box 
            sx={{ 
              display: 'flex', 
              justifyContent: 'center',
              color: (theme) => theme.palette.text.secondary,
              fontSize: '0.875rem',
            }}
          >
            Meeting Bot &copy; {new Date().getFullYear()} - Built with Vite & React
          </Box>
        </Container>
      </Box>

      {/* Scroll to top button */}
      <ScrollTop />

      {/* Global notification snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseNotification} 
          severity={notification.severity} 
          variant="filled"
          elevation={6}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Layout; 