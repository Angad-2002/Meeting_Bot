import { Box, CircularProgress, Typography } from '@mui/material';
import { motion } from 'framer-motion';

const loadingContainer = {
  width: "2rem",
  height: "2rem",
  display: "flex",
  justifyContent: "space-around",
};

const loadingCircle = {
  display: "block",
  width: "0.5rem",
  height: "0.5rem",
  backgroundColor: "primary.main",
  borderRadius: "0.25rem",
};

const loadingContainerVariants = {
  start: {
    transition: {
      staggerChildren: 0.2,
    },
  },
  end: {
    transition: {
      staggerChildren: 0.2,
    },
  },
};

const loadingCircleVariants = {
  start: {
    y: "0%",
  },
  end: {
    y: "100%",
  },
};

const loadingCircleTransition = {
  duration: 0.5,
  repeat: Infinity,
  repeatType: "reverse",
  ease: "easeInOut",
};

function LoadingScreen({ message = 'Loading...' }) {
  return (
    <Box 
      sx={{ 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '60vh' 
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
      >
        <CircularProgress 
          size={60} 
          thickness={4} 
          sx={{ mb: 3 }}
        />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Typography 
          variant="h6" 
          color="text.secondary" 
          sx={{ mb: 4 }}
        >
          {message}
        </Typography>
      </motion.div>

      <motion.div
        style={loadingContainer}
        variants={loadingContainerVariants}
        initial="start"
        animate="end"
      >
        <motion.span
          style={loadingCircle}
          variants={loadingCircleVariants}
          transition={loadingCircleTransition}
          sx={{ backgroundColor: 'primary.main' }}
        />
        <motion.span
          style={loadingCircle}
          variants={loadingCircleVariants}
          transition={loadingCircleTransition}
          sx={{ backgroundColor: 'secondary.main' }}
        />
        <motion.span
          style={loadingCircle}
          variants={loadingCircleVariants}
          transition={loadingCircleTransition}
          sx={{ backgroundColor: 'primary.dark' }}
        />
      </motion.div>
    </Box>
  );
}

export default LoadingScreen; 