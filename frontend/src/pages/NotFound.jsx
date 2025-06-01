import { Box, Typography, Button } from '@mui/material';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

function NotFound() {
  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      minHeight: '70vh',
      textAlign: 'center'
    }}>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Typography 
          variant="h1" 
          color="primary" 
          sx={{ 
            fontSize: { xs: '6rem', md: '10rem' }, 
            fontWeight: 700,
            textShadow: '2px 2px 8px rgba(0,0,0,0.1)'
          }}
        >
          404
        </Typography>
      </motion.div>
      
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.6 }}
      >
        <Typography 
          variant="h4" 
          color="text.secondary" 
          sx={{ mb: 2, fontWeight: 500 }}
        >
          Page Not Found
        </Typography>
        
        <Typography 
          variant="body1" 
          color="text.secondary" 
          sx={{ mb: 4, maxWidth: 500 }}
        >
          The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.
        </Typography>
        
        <Button 
          component={Link} 
          to="/" 
          variant="contained" 
          color="primary"
          size="large"
        >
          Go to Home
        </Button>
      </motion.div>
    </Box>
  );
}

export default NotFound; 