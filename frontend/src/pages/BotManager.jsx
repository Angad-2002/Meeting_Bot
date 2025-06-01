import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Grid,
  TextField,
  Button,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  useTheme,
  Card,
  CardContent,
  CardActionArea,
  Divider,
  Switch,
  FormControlLabel,
  CardHeader,
  Avatar,
  FormHelperText,
  Chip,
} from '@mui/material';
import { motion } from 'framer-motion';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SettingsIcon from '@mui/icons-material/Settings';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import PublicIcon from '@mui/icons-material/Public';
import apiService from '../services/api';

// Steps for bot creation process
const steps = ['Select Persona', 'Configure Settings', 'Launch Bot'];

function BotManager() {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const queryParams = new URLSearchParams(location.search);
  const preselectedPersonaId = queryParams.get('persona');

  // State
  const [activeStep, setActiveStep] = useState(0);
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    persona_id: preselectedPersonaId ? [preselectedPersonaId] : [],
    meeting_name: '',
    meeting_type: 'general',
    voice_enabled: true,
    auto_join: true,
    context_info: '',
    meeting_url: '',
    entry_message: '',
    text_message: ''
  });

  useEffect(() => {
    fetchPersonas();
    
    // If persona is preselected, move to next step
    if (preselectedPersonaId) {
      setActiveStep(1);
    }
  }, [preselectedPersonaId]);

  const fetchPersonas = async () => {
    try {
      setLoading(true);
      const response = await apiService.getPersonas();
      setPersonas(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching personas:', err);
      setError(err.message || 'Failed to fetch personas');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, checked } = e.target;
    const newValue = e.target.type === 'checkbox' ? checked : value;
    setFormData(prev => ({ ...prev, [name]: newValue }));
  };

  const handlePersonaSelect = (personaId) => {
    setFormData(prev => {
      // If this persona is already selected, remove it, otherwise add it
      const newPersonaIds = prev.persona_id.includes(personaId)
        ? prev.persona_id.filter(id => id !== personaId)
        : [...prev.persona_id, personaId];
      
      // Get the newly selected persona (if there is one)
      const selectedPersona = personas.find(p => p.id === personaId);
      let updatedData = { ...prev, persona_id: newPersonaIds };
      
      // If we just added a persona, update the entry_message and text_message with the persona's defaults
      if (selectedPersona && !prev.persona_id.includes(personaId)) {
        const defaultEntryMessage = selectedPersona.entry_message || '';
        const personaName = selectedPersona.name || 'Bot';
        
        // Only set these if they're empty or if we're changing from no persona to having a persona
        if (!prev.entry_message || prev.persona_id.length === 0) {
          updatedData.entry_message = defaultEntryMessage;
        }
        
        if (!prev.text_message || prev.persona_id.length === 0) {
          updatedData.text_message = `${personaName} has joined the meeting.`;
        }
      }
      
      return updatedData;
    });
    
    // Only proceed to next step if at least one persona is selected
    // This is handled by a continue button now, not automatic
  };

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleCreateBot = async () => {
    try {
      setCreating(true);
      setError(null);

      // Create a copy of the form data to modify for API call
      const apiFormData = {
        ...formData,
        // Use the persona_id array directly as personas array
        personas: formData.persona_id.map(id => {
          // Find the persona by ID
          const persona = personas.find(p => p.id === id);
          // If the persona has a display name containing "Executive CXO", use "cxo_executive"
          if (persona.name.includes("Executive CXO")) {
            return "cxo_executive";
          }
          // Otherwise just use the ID which should be the folder name
          return id;
        }),
        // Set bot_name to the meeting_name if not already set
        bot_name: formData.meeting_name
      };
      
      // Debug logs
      console.log('Creating bot with data:', apiFormData);
      console.log('Selected persona IDs:', formData.persona_id);
      console.log('Selected persona details:', formData.persona_id.map(id => personas.find(p => p.id === id)));

      // API call to create bot
      await apiService.createBot(apiFormData);
      setSuccess('Bot created successfully!');
      
      // Navigate to active bots after a short delay
      setTimeout(() => {
        navigate('/active-bots');
      }, 1500);
    } catch (err) {
      console.error('Error creating bot:', err);
      // Make sure to extract error message as a string
      setError(typeof err.message === 'object' ? JSON.stringify(err.message) : err.message || 'Failed to create bot. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  // Get selected persona details
  const selectedPersonas = formData.persona_id.map(id => personas.find(p => p.id === id)).filter(Boolean);

  // Step content
  const getStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <SelectPersonaStep 
            personas={personas} 
            loading={loading} 
            selectedPersonaIds={formData.persona_id}
            onSelect={handlePersonaSelect}
          />
        );
      case 1:
        return (
          <ConfigureSettingsStep 
            formData={formData}
            onChange={handleChange}
            selectedPersonas={selectedPersonas}
          />
        );
      case 2:
        return (
          <LaunchBotStep 
            formData={formData}
            selectedPersonas={selectedPersonas}
            creating={creating}
            onLaunch={handleCreateBot}
          />
        );
      default:
        return 'Unknown step';
    }
  };

  return (
    <Container maxWidth="lg">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography 
          variant="h4" 
          component="h1" 
          color="primary.dark"
          sx={{ 
            fontWeight: 700,
            mb: 4,
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
          Create Bot
        </Typography>
        
        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 3, borderRadius: 2 }}
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        )}
        
        {success && (
          <Alert 
            severity="success" 
            sx={{ mb: 3, borderRadius: 2 }}
          >
            {success}
          </Alert>
        )}
        
        <Paper 
          elevation={2} 
          sx={{ 
            p: 4, 
            borderRadius: 3,
            backgroundColor: '#ffffff',
            mb: 4
          }}
        >
          <Stepper 
            activeStep={activeStep} 
            alternativeLabel
            sx={{ mb: 4 }}
          >
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
          
          <Box sx={{ mt: 2 }}>
            {getStepContent(activeStep)}
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4, pt: 2, borderTop: `1px solid ${theme.palette.grey[200]}` }}>
            <Button
              variant="outlined"
              disabled={activeStep === 0 || creating}
              onClick={handleBack}
              startIcon={<ArrowBackIcon />}
            >
              Back
            </Button>
            
            <Box>
              {activeStep === 0 && (
                <>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/')}
                    sx={{ mr: 2 }}
                  >
                    Cancel
                  </Button>
                  
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleNext}
                    endIcon={<ArrowForwardIcon />}
                    disabled={formData.persona_id.length === 0}
                  >
                    Continue
                  </Button>
                </>
              )}
              
              {activeStep === 1 && (
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleNext}
                  endIcon={<ArrowForwardIcon />}
                >
                  Continue
                </Button>
              )}
            </Box>
          </Box>
        </Paper>
      </motion.div>
    </Container>
  );
}

// Step 1: Select Persona
function SelectPersonaStep({ personas, loading, selectedPersonaIds, onSelect }) {
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h6" color="primary" gutterBottom>
        Select Personas for your Bot
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Choose one or more personas that will define your bot's identity, conversational style, and knowledge base.
        Click on personas to select or deselect them.
      </Typography>
      
      <Box 
        sx={{ 
          mb: 3, 
          p: 2, 
          backgroundColor: 'info.light', 
          color: 'info.contrastText',
          borderRadius: 1
        }}
      >
        <Typography variant="body2">
          You have selected {selectedPersonaIds.length} {selectedPersonaIds.length === 1 ? 'persona' : 'personas'}.
          {selectedPersonaIds.length > 0 && ' Click "Continue" to proceed.'}
        </Typography>
      </Box>
      
      <Grid container spacing={2} sx={{ mt: 2 }}>
        {personas.map((persona) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={persona.id}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                height: '100%',
                border: selectedPersonaIds.includes(persona.id) ? `2px solid ${persona.color || '#3a86ff'}` : '1px solid transparent',
                borderRadius: 3,
                boxShadow: selectedPersonaIds.includes(persona.id) ? '0px 4px 20px rgba(0, 0, 0, 0.15)' : '0px 2px 8px rgba(0, 0, 0, 0.05)',
                transition: 'all 0.3s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.15)',
                },
              }}
              onClick={() => onSelect(persona.id)}
            >
              {selectedPersonaIds.includes(persona.id) && (
                <Box 
                  sx={{ 
                    position: 'absolute', 
                    top: -12, 
                    right: -12, 
                    zIndex: 1, 
                    backgroundColor: 'white',
                    borderRadius: '50%' 
                  }}
                >
                  <CheckCircleIcon color="primary" sx={{ fontSize: 28 }} />
                </Box>
              )}
              
              <CardActionArea 
                sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}
              >
                <Box 
                  sx={{ 
                    height: 100, 
                    backgroundColor: persona.image ? 'transparent' : 'primary.light',
                    backgroundImage: persona.image ? `url(${persona.image})` : 'none',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: persona.image ? 'transparent' : 'white',
                    fontSize: '2rem',
                    fontWeight: 'bold'
                  }}
                >
                  {!persona.image && (persona.name?.charAt(0) || '?')}
                </Box>
                <CardContent>
                  <Typography variant="h6" component="div" gutterBottom>
                    {persona.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {persona.description?.substring(0, 120)}
                    {persona.description?.length > 120 ? '...' : ''}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
        
        {personas.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Paper 
              sx={{ 
                p: 4, 
                textAlign: 'center',
                backgroundColor: 'rgba(0,0,0,0.02)',
                borderRadius: 2,
                border: '1px dashed rgba(0,0,0,0.1)'
              }}
            >
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No personas available
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Create a persona first to use in your bot
              </Typography>
              <Button 
                variant="contained" 
                color="primary"
                onClick={() => navigate('/personas/new')}
              >
                Create New Persona
              </Button>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

// Step 2: Configure Settings
function ConfigureSettingsStep({ formData, onChange, selectedPersonas }) {
  // Check if the CXO persona is selected
  const isCxoSelected = selectedPersonas.some(persona => 
    persona.id.toLowerCase().includes('cxo') || 
    persona.name.toLowerCase().includes('cxo') ||
    persona.name.toLowerCase().includes('executive')
  );

  // Get context field helper text based on selected persona
  const getContextHelperText = () => {
    if (isCxoSelected) {
      return "Provide business context for the CXO. Include company KPIs, meeting objectives, any metrics or outstanding issues - this will be used by the executive to ask relevant questions.";
    }
    return "This information will guide the bot's responses and knowledge";
  };

  // Get context field placeholder based on selected persona
  const getContextPlaceholder = () => {
    if (isCxoSelected) {
      return "e.g., Q3 sales are down 15% vs target. EBITDA margin at 22%. Key agenda: 1) Addressing sales pipeline gaps 2) Discussing new product launch timeline 3) Reviewing budget allocation for Q4";
    }
    return "Provide any additional context for the bot (optional)";
  };

  return (
    <Box>
      <Typography variant="h6" color="primary" gutterBottom>
        Configure Bot Settings
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Configure how your bot will behave in the meeting
      </Typography>
      
      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom fontWeight={500}>
              Selected Personas ({selectedPersonas.length}):
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {selectedPersonas.map(persona => (
                <Chip 
                  key={persona.id}
                  label={persona.name}
                  color="primary"
                  variant="outlined"
                  avatar={persona.image ? <Avatar src={persona.image} /> : undefined}
                />
              ))}
            </Box>
          </Box>
          
          <TextField
            label="Meeting Name"
            name="meeting_name"
            value={formData.meeting_name}
            onChange={onChange}
            fullWidth
            variant="outlined"
            margin="normal"
            required
            placeholder="Enter a name for this meeting"
          />
          
          <TextField
            label="Meeting URL"
            name="meeting_url"
            value={formData.meeting_url}
            onChange={onChange}
            fullWidth
            variant="outlined"
            margin="normal"
            required
            placeholder="Enter the meeting URL"
            helperText="Required URL where the bot will join the meeting"
          />
          
          <FormControl fullWidth margin="normal">
            <InputLabel id="meeting-type-label">Meeting Type</InputLabel>
            <Select
              labelId="meeting-type-label"
              name="meeting_type"
              value={formData.meeting_type}
              onChange={onChange}
              label="Meeting Type"
            >
              <MenuItem value="general">General Discussion</MenuItem>
              <MenuItem value="interview">Interview</MenuItem>
              <MenuItem value="workshop">Workshop</MenuItem>
              <MenuItem value="presentation">Presentation</MenuItem>
              <MenuItem value="qa">Q&A Session</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="Welcome Chat Message"
            name="entry_message"
            value={formData.entry_message}
            onChange={onChange}
            fullWidth
            variant="outlined"
            margin="normal"
            placeholder="Message the bot will post in chat when joining the meeting"
            helperText="This will be posted in the meeting chat, not spoken"
          />
          
          <TextField
            label="Initial Speech"
            name="text_message"
            value={formData.text_message}
            onChange={onChange}
            fullWidth
            variant="outlined"
            margin="normal"
            placeholder="What the bot will say out loud when joining"
            helperText="This is what the bot will speak when joining, not shown in chat"
          />
          
          <TextField
            label="Context Information"
            name="context_info"
            value={formData.context_info}
            onChange={onChange}
            fullWidth
            variant="outlined"
            margin="normal"
            multiline
            rows={4}
            placeholder={getContextPlaceholder()}
            helperText={getContextHelperText()}
          />
          
          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.voice_enabled}
                  onChange={onChange}
                  name="voice_enabled"
                  color="primary"
                />
              }
              label="Enable Voice"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={formData.auto_join}
                  onChange={onChange}
                  name="auto_join"
                  color="primary"
                />
              }
              label="Auto-join meeting when ready"
            />
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

// Step 3: Launch Bot
function LaunchBotStep({ formData, selectedPersonas, creating, onLaunch }) {
  // Check if context info is provided
  const hasContextInfo = formData.context_info && formData.context_info.trim().length > 0;
  
  // Truncate long context info for display
  const getDisplayContextInfo = () => {
    if (!hasContextInfo) return 'None provided';
    
    const maxLength = 100;
    const contextInfo = formData.context_info.trim();
    if (contextInfo.length <= maxLength) return contextInfo;
    return `${contextInfo.substring(0, maxLength)}...`;
  };

  return (
    <Box>
      <Typography variant="h6" color="primary" gutterBottom>
        Ready to Launch Bot
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Review your settings and launch your bot
      </Typography>
      
      <Paper variant="outlined" sx={{ p: 3, mb: 4, borderRadius: 2 }}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Personas ({selectedPersonas.length})
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, my: 1 }}>
              {selectedPersonas.map(persona => (
                <Chip 
                  key={persona.id}
                  label={persona.name}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
            
            <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>
              Meeting Name
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {formData.meeting_name || 'Unnamed Meeting'}
            </Typography>
            
            <Typography variant="subtitle2" color="text.secondary">
              Meeting Type
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {formData.meeting_type.charAt(0).toUpperCase() + formData.meeting_type.slice(1)}
            </Typography>
          </Grid>
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Meeting URL
            </Typography>
            <Typography 
              variant="body2" 
              sx={{ 
                mb: 1, 
                wordBreak: 'break-all',
                color: formData.meeting_url ? 'text.primary' : 'error.main'
              }}
            >
              {formData.meeting_url || 'Missing URL (required)'}
            </Typography>
            
            <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 2 }}>
              Entry Message
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {formData.entry_message || 'None'}
            </Typography>
            
            <Typography variant="subtitle2" color="text.secondary">
              Initial Speech
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {formData.text_message || 'None'}
            </Typography>
            
            <Typography variant="subtitle2" color="text.secondary">
              Context Information {hasContextInfo && <Chip size="small" label="Provided" color="success" variant="outlined" />}
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {getDisplayContextInfo()}
            </Typography>
          </Grid>
        </Grid>
      </Paper>
      
      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <Button
          variant="contained"
          color="primary"
          size="large"
          onClick={onLaunch}
          disabled={creating || !formData.meeting_url}
          startIcon={creating ? <CircularProgress size={20} color="inherit" /> : null}
          sx={{ minWidth: 200 }}
        >
          {creating ? 'Launching...' : 'Launch Bot'}
        </Button>
      </Box>
      
      {!formData.meeting_url && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Meeting URL is required to launch the bot
        </Alert>
      )}
    </Box>
  );
}

export default BotManager; 