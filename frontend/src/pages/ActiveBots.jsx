import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Grid,
  Button,
  Paper,
  Card,
  CardContent,
  CardActions,
  CardHeader,
  Avatar,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Tooltip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  useTheme,
} from '@mui/material';
import { motion, AnimatePresence } from 'framer-motion';
import AddIcon from '@mui/icons-material/Add';
import StopIcon from '@mui/icons-material/Stop';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import LinkIcon from '@mui/icons-material/Link';
import RefreshIcon from '@mui/icons-material/Refresh';
import apiService from '../services/api';

function ActiveBots() {
  const navigate = useNavigate();
  const theme = useTheme();
  const [bots, setBots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [stopping, setStopping] = useState(null); // id of bot being stopped
  const [stopDialogOpen, setStopDialogOpen] = useState(false);
  const [botToStop, setBotToStop] = useState(null);

  useEffect(() => {
    fetchActiveBots();
    
    // Set up polling for active bots
    const interval = setInterval(() => {
      fetchActiveBots(true);
    }, 30000); // Poll every 30 seconds
    
    return () => {
      clearInterval(interval);
    };
  }, []);

  const fetchActiveBots = async (silent = false) => {
    try {
      if (!silent) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      
      const response = await apiService.getActiveBots();
      setBots(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching active bots:', err);
      // Handle 404 differently - it's likely the endpoint isn't implemented yet
      if (err.status === 404) {
        setBots([]);
        if (!silent) {
          setError("The active bots API endpoint is not available yet. This feature is under development. When implemented, you'll be able to see and manage all your running bots here.");
        }
      } else {
        if (!silent) {
          setError(err.message || 'Failed to fetch active bots');
        }
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    fetchActiveBots(true);
  };

  const handleCreateBot = () => {
    navigate('/bots');
  };

  const handleStopBot = (bot) => {
    setBotToStop(bot);
    setStopDialogOpen(true);
  };

  const confirmStopBot = async () => {
    if (!botToStop) return;
    
    try {
      setStopping(botToStop.id);
      await apiService.stopBot(botToStop.id);
      
      // Remove the bot from the list
      setBots(bots.filter(b => b.id !== botToStop.id));
      setStopDialogOpen(false);
      setBotToStop(null);
    } catch (err) {
      console.error('Error stopping bot:', err);
      setError(`Failed to stop bot: ${err.message || 'Unknown error'}`);
    } finally {
      setStopping(null);
    }
  };

  const handleCopyMeetingLink = (meetingUrl) => {
    navigator.clipboard.writeText(meetingUrl);
    window.showNotification('Meeting link copied to clipboard', 'success');
  };

  const handleJoinMeeting = (meetingUrl) => {
    window.open(meetingUrl, '_blank');
  };

  // Loading state
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="70vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography 
            variant="h4" 
            component="h1" 
            color="primary.dark"
            sx={{ 
              fontWeight: 700,
              textShadow: '1px 1px 2px rgba(0,0,0,0.1)',
              position: 'relative',
              '&::after': {
                content: '""',
                position: 'absolute',
                bottom: -8,
                left: 0,
                width: '60px',
                height: '4px',
                borderRadius: '2px',
                backgroundColor: theme.palette.secondary.main
              }
            }}
          >
            Active Bots
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Tooltip title="Refresh">
              <IconButton 
                onClick={handleRefresh} 
                disabled={refreshing}
                color="primary"
                sx={{ 
                  backgroundColor: theme.palette.grey[100],
                  '&:hover': {
                    backgroundColor: theme.palette.grey[200]
                  }
                }}
              >
                {refreshing ? <CircularProgress size={24} /> : <RefreshIcon />}
              </IconButton>
            </Tooltip>
            
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={handleCreateBot}
              sx={{
                borderRadius: '28px',
                boxShadow: theme.shadows[2],
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: theme.shadows[4],
                },
                transition: 'all 0.3s',
              }}
            >
              Create New Bot
            </Button>
          </Box>
        </Box>
        
        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 3, borderRadius: 2 }}
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        )}
        
        {bots.length > 0 ? (
          <Grid container spacing={3}>
            <AnimatePresence>
              {bots.map((bot) => (
                <Grid size={{ xs: 12, md: 6 }} key={bot.id}>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Card 
                      sx={{ 
                        height: '100%',
                        borderRadius: 3,
                        boxShadow: theme.shadows[2],
                        transition: 'all 0.3s',
                        '&:hover': {
                          boxShadow: theme.shadows[5],
                          transform: 'translateY(-4px)',
                        },
                        position: 'relative',
                        overflow: 'visible',
                      }}
                    >
                      <CardHeader
                        avatar={
                          <Avatar
                            src={bot.persona?.image}
                            sx={{ 
                              width: 56, 
                              height: 56, 
                              bgcolor: bot.persona?.image ? 'transparent' : 'primary.light',
                              boxShadow: theme.shadows[2],
                            }}
                          >
                            {!bot.persona?.image && (bot.persona?.name?.charAt(0) || 'B')}
                          </Avatar>
                        }
                        title={
                          <Typography variant="h6" fontWeight={600}>
                            {bot.meeting_name || 'Unnamed Bot'}
                          </Typography>
                        }
                        subheader={
                          <Typography variant="body2" color="text.secondary">
                            {bot.persona?.name || 'Unknown Persona'}
                          </Typography>
                        }
                        action={
                          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                            <Chip 
                              label={bot.status || 'Active'} 
                              color={bot.status === 'active' ? 'success' : 'primary'}
                              size="small"
                              sx={{ mr: 1, textTransform: 'capitalize' }}
                            />
                            {bot.voice_enabled ? (
                              <Tooltip title="Voice Enabled">
                                <MicIcon color="success" fontSize="small" />
                              </Tooltip>
                            ) : (
                              <Tooltip title="Voice Disabled">
                                <MicOffIcon color="disabled" fontSize="small" />
                              </Tooltip>
                            )}
                          </Box>
                        }
                      />
                      
                      <Divider sx={{ mx: 2 }} />
                      
                      <CardContent>
                        <Grid container spacing={2}>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              Meeting Type
                            </Typography>
                            <Typography variant="body1" gutterBottom>
                              {bot.meeting_type 
                                ? bot.meeting_type.charAt(0).toUpperCase() + bot.meeting_type.slice(1) 
                                : 'General'
                              }
                            </Typography>
                          </Grid>
                          
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              Started At
                            </Typography>
                            <Typography variant="body1" gutterBottom>
                              {bot.created_at 
                                ? new Date(bot.created_at).toLocaleString() 
                                : 'Unknown'
                              }
                            </Typography>
                          </Grid>
                        </Grid>
                        
                        {bot.meeting_url && (
                          <Box sx={{ mt: 2 }}>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              Meeting URL
                            </Typography>
                            <Box sx={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              mt: 1,
                              p: 1.5,
                              borderRadius: 2,
                              backgroundColor: theme.palette.grey[50],
                              border: `1px solid ${theme.palette.grey[200]}`,
                            }}>
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  flexGrow: 1, 
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  fontFamily: 'monospace'
                                }}
                              >
                                {bot.meeting_url}
                              </Typography>
                              <Tooltip title="Copy Meeting Link">
                                <IconButton 
                                  size="small" 
                                  onClick={() => handleCopyMeetingLink(bot.meeting_url)}
                                  sx={{ ml: 1 }}
                                >
                                  <LinkIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </Box>
                        )}
                      </CardContent>
                      
                      <CardActions sx={{ p: 2, pt: 0, justifyContent: 'space-between' }}>
                        <Button
                          variant="contained"
                          color="error"
                          startIcon={stopping === bot.id ? <CircularProgress size={20} color="inherit" /> : <StopIcon />}
                          onClick={() => handleStopBot(bot)}
                          disabled={stopping === bot.id}
                          size="small"
                        >
                          {stopping === bot.id ? 'Stopping...' : 'Remove Bot'}
                        </Button>
                        
                        {bot.meeting_url && (
                          <Button
                            variant="contained"
                            color="primary"
                            onClick={() => handleJoinMeeting(bot.meeting_url)}
                            size="small"
                          >
                            Join Meeting
                          </Button>
                        )}
                      </CardActions>
                    </Card>
                  </motion.div>
                </Grid>
              ))}
            </AnimatePresence>
          </Grid>
        ) : (
          <Paper 
            sx={{ 
              p: 6, 
              textAlign: 'center',
              borderRadius: 3,
              backgroundColor: 'rgba(0,0,0,0.02)',
              border: '1px dashed rgba(0,0,0,0.1)'
            }}
          >
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No Active Bots
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              You don't have any bots running. Create a new bot to get started.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={handleCreateBot}
              sx={{ mt: 2 }}
            >
              Create New Bot
            </Button>
          </Paper>
        )}
      </motion.div>
      
      {/* Confirmation Dialog */}
      <Dialog
        open={stopDialogOpen}
        onClose={() => setStopDialogOpen(false)}
        aria-labelledby="stop-bot-dialog-title"
      >
        <DialogTitle id="stop-bot-dialog-title">
          Remove Bot
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to remove the bot "{botToStop?.meeting_name}"?
            This action cannot be undone, and the bot will immediately disconnect from the meeting.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setStopDialogOpen(false)} 
            disabled={stopping === botToStop?.id}
          >
            Cancel
          </Button>
          <Button 
            onClick={confirmStopBot} 
            variant="contained" 
            color="error"
            disabled={stopping === botToStop?.id}
            startIcon={stopping === botToStop?.id && <CircularProgress size={16} color="inherit" />}
          >
            {stopping === botToStop?.id ? 'Removing...' : 'Remove Bot'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default ActiveBots; 