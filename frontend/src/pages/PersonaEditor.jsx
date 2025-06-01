import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Grid,
  TextField,
  Button,
  Paper,
  Divider,
  Alert,
  Chip,
  IconButton,
  Avatar,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  useTheme,
  CircularProgress,
  OutlinedInput,
} from '@mui/material';
import { motion } from 'framer-motion';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import DeleteIcon from '@mui/icons-material/Delete';
import AddPhotoAlternateIcon from '@mui/icons-material/AddPhotoAlternate';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import apiService from '../services/api';

function PersonaEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const theme = useTheme();
  const isNewPersona = !id || id === 'new';

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    personality: '',
    knowledge_base: '',
    image: '',
    entry_message: '',
    voice_id: '',
    gender: 'NEUTRAL',
    characteristics: [],
  });

  // UI state
  const [loading, setLoading] = useState(!isNewPersona);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [newCharacteristic, setNewCharacteristic] = useState('');
  const [formErrors, setFormErrors] = useState({});
  const [imageUrl, setImageUrl] = useState('');
  const [imageLoading, setImageLoading] = useState(false);
  const [generatingImage, setGeneratingImage] = useState(false);

  // Load persona data if editing
  useEffect(() => {
    if (!isNewPersona) {
      fetchPersona();
    }
  }, [id]);

  const fetchPersona = async () => {
    try {
      setLoading(true);
      const response = await apiService.getPersona(id);
      setFormData(response.data);
      setImageUrl(response.data.image);
      setError(null);
    } catch (err) {
      console.error('Error fetching persona:', err);
      setError('Could not load persona. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear validation error for this field if any
    if (formErrors[name]) {
      setFormErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const handleAddCharacteristic = () => {
    if (newCharacteristic.trim()) {
      setFormData(prev => ({
        ...prev,
        characteristics: [...(prev.characteristics || []), newCharacteristic.trim()]
      }));
      setNewCharacteristic('');
    }
  };

  const handleDeleteCharacteristic = (index) => {
    setFormData(prev => ({
      ...prev,
      characteristics: prev.characteristics.filter((_, i) => i !== index)
    }));
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.name?.trim()) {
      errors.name = 'Name is required';
    }
    
    if (!formData.description?.trim()) {
      errors.description = 'Description is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      
      if (isNewPersona) {
        await apiService.createPersona(formData);
        setSuccess('Persona created successfully!');
      } else {
        await apiService.updatePersona(id, formData);
        setSuccess('Persona updated successfully!');
      }
      
      // Navigate back after a short delay to show success message
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (err) {
      console.error('Error saving persona:', err);
      setError(err.message || 'Failed to save persona. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/');
  };

  const handleImageUpload = async (e) => {
    setImageLoading(true);
    const file = e.target.files[0];
    if (file) {
      const formData = new FormData();
      formData.append('image', file);
      try {
        const response = await apiService.uploadImage(formData);
        setImageUrl(response.data.url);
        setFormData(prev => ({ ...prev, image: response.data.url }));
        setError(null);
      } catch (err) {
        console.error('Error uploading image:', err);
        setError('Failed to upload image. Please try again.');
      } finally {
        setImageLoading(false);
      }
    }
  };

  const handleDeleteImage = () => {
    setImageUrl('');
    setFormData(prev => ({ ...prev, image: '' }));
  };

  const handleGenerate = async () => {
    setGeneratingImage(true);
    try {
      const response = await apiService.generateImage(formData);
      setImageUrl(response.data.url);
      setFormData(prev => ({ ...prev, image: response.data.url }));
      setError(null);
    } catch (err) {
      console.error('Error generating image:', err);
      setError('Failed to generate image. Please try again.');
    } finally {
      setGeneratingImage(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
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
        <Box sx={{ mb: 4, display: 'flex', alignItems: 'center' }}>
          <Button
            color="inherit"
            startIcon={<ArrowBackIcon />}
            onClick={handleCancel}
            sx={{ mr: 2 }}
          >
            Back
          </Button>
          <Typography 
            variant="h4" 
            component="h1" 
            sx={{ 
              flexGrow: 1, 
              fontWeight: 600,
              color: 'primary.dark'
            }}
          >
            {isNewPersona ? 'Create New Persona' : 'Edit Persona'}
          </Typography>
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
          component="form"
          onSubmit={handleSubmit}
          sx={{ 
            p: 4, 
            borderRadius: 3,
            backgroundColor: '#ffffff',
          }}
        >
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 4 }}>
              {imageUrl ? (
                <Box sx={{ position: 'relative' }}>
                  <Box sx={{ position: 'relative', paddingTop: '100%', overflow: 'hidden' }}>
                    <Box
                      component="img"
                      src={imageUrl}
                      alt={formData.name || 'Persona'}
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        borderRadius: 2,
                        boxShadow: theme.shadows[2],
                      }}
                    />
                  </Box>

                  <Button
                    variant="contained"
                    component="label"
                    startIcon={<AddPhotoAlternateIcon />}
                    loading={imageLoading}
                    loadingPosition="start"
                    sx={{
                      position: 'absolute',
                      bottom: 10,
                      left: 10,
                      borderRadius: '20px',
                    }}
                  >
                    Change
                    <input
                      type="file"
                      hidden
                      accept="image/*"
                      onChange={handleImageUpload}
                    />
                  </Button>

                  <IconButton
                    color="error"
                    onClick={handleDeleteImage}
                    sx={{
                      position: 'absolute',
                      top: 10,
                      right: 10,
                      bgcolor: 'background.paper',
                      boxShadow: theme.shadows[3],
                      '&:hover': {
                        bgcolor: 'error.light',
                        color: 'white',
                      },
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    border: `2px dashed ${theme.palette.grey[400]}`,
                    borderRadius: 2,
                    p: 4,
                    height: '100%',
                    minHeight: 250,
                  }}
                >
                  <AddPhotoAlternateIcon
                    sx={{ fontSize: 60, color: theme.palette.grey[400], mb: 2 }}
                  />
                  <Typography
                    variant="body1"
                    sx={{ mb: 3, textAlign: 'center', color: theme.palette.grey[600] }}
                  >
                    Upload a profile image for your persona
                  </Typography>

                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Button
                      variant="contained"
                      component="label"
                      startIcon={<AddPhotoAlternateIcon />}
                      loading={imageLoading}
                      loadingPosition="start"
                    >
                      Upload Image
                      <input
                        type="file"
                        hidden
                        accept="image/*"
                        onChange={handleImageUpload}
                      />
                    </Button>

                    <Button
                      variant="outlined"
                      onClick={handleGenerate}
                      startIcon={<AutoFixHighIcon />}
                      disabled={!formData.name || generatingImage}
                    >
                      {generatingImage ? 'Generating...' : 'Auto-Generate'}
                    </Button>
                  </Box>
                </Box>
              )}
            </Grid>
            
            <Grid size={{ xs: 12, md: 8 }}>
              <Box>
                <TextField
                  label="Name"
                  name="name"
                  value={formData.name || ''}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  margin="normal"
                  required
                  error={!!formErrors.name}
                  helperText={formErrors.name}
                />
                
                <TextField
                  label="Description"
                  name="description"
                  value={formData.description || ''}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  margin="normal"
                  required
                  multiline
                  rows={3}
                  error={!!formErrors.description}
                  helperText={formErrors.description}
                />
                
                <TextField
                  label="Personality"
                  name="personality"
                  value={formData.personality || ''}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  margin="normal"
                  multiline
                  rows={3}
                  helperText="Describe the persona's personality traits and conversational style"
                />
                
                <TextField
                  label="Knowledge Base"
                  name="knowledge_base"
                  value={formData.knowledge_base || ''}
                  onChange={handleChange}
                  fullWidth
                  variant="outlined"
                  margin="normal"
                  multiline
                  rows={2}
                  helperText="Describe the persona's areas of expertise or knowledge"
                />
                
                <Divider sx={{ my: 3 }} />
                
                <Typography variant="h6" color="primary.dark" gutterBottom>
                  Speech Settings
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 7 }}>
                    <TextField
                      label="Entry Message"
                      name="entry_message"
                      value={formData.entry_message || ''}
                      onChange={handleChange}
                      fullWidth
                      variant="outlined"
                      margin="normal"
                      helperText="First message the persona will say when joining"
                    />
                  </Grid>
                  
                  <Grid size={{ xs: 12, sm: 5 }}>
                    <FormControl fullWidth margin="normal">
                      <InputLabel id="gender-label">Voice Gender</InputLabel>
                      <Select
                        labelId="gender-label"
                        name="gender"
                        value={formData.gender || 'NEUTRAL'}
                        onChange={handleChange}
                        label="Voice Gender"
                      >
                        <MenuItem value="MALE">Male</MenuItem>
                        <MenuItem value="FEMALE">Female</MenuItem>
                        <MenuItem value="NEUTRAL">Neutral</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  
                  <Grid size={{ xs: 12 }}>
                    <TextField
                      label="Voice ID"
                      name="voice_id"
                      value={formData.voice_id || ''}
                      onChange={handleChange}
                      fullWidth
                      variant="outlined"
                      margin="normal"
                      helperText="Custom voice ID for text-to-speech (if available)"
                    />
                  </Grid>
                </Grid>
              </Box>
            </Grid>
          </Grid>
          
          <Box sx={{ mt: 6, display: 'flex', justifyContent: 'space-between' }}>
            <Button
              variant="outlined"
              color="inherit"
              onClick={handleCancel}
              disabled={saving}
            >
              Cancel
            </Button>
            
            <Box sx={{ display: 'flex', gap: 2 }}>
              {!isNewPersona && (
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<DeleteIcon />}
                  disabled={saving}
                  onClick={() => {
                    if (confirm('Are you sure you want to delete this persona?')) {
                      // Implement delete logic here
                    }
                  }}
                >
                  Delete
                </Button>
              )}
              
              <Button
                type="submit"
                variant="contained"
                color="primary"
                startIcon={saving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Persona'}
              </Button>
            </Box>
          </Box>
        </Paper>
      </motion.div>
    </Container>
  );
}

export default PersonaEditor; 