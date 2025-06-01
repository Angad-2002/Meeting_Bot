import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Grid,
  TextField,
  InputAdornment,
  Button,
  Alert,
  Skeleton,
  Fade,
  useTheme,
} from '@mui/material';
import { motion } from 'framer-motion';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import SortIcon from '@mui/icons-material/Sort';
import PersonaCard from '../components/PersonaCard';
import apiService from '../services/api';

function PersonaList() {
  const theme = useTheme();
  const navigate = useNavigate();
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('name'); // 'name', 'newest', 'updated'

  useEffect(() => {
    fetchPersonas();
  }, []);

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

  const handleCreatePersona = () => {
    navigate('/personas/new');
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleSort = (sortType) => {
    setSortBy(sortType);
  };

  // Filter and sort personas
  const filteredPersonas = personas
    .filter(persona =>
      persona.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      persona.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      persona.personality?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'name') {
        return a.name?.localeCompare(b.name);
      } else if (sortBy === 'newest') {
        return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      } else if (sortBy === 'updated') {
        return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
      }
      return 0;
    });

  // Loading skeletons for the grid
  const renderSkeletons = () => {
    return Array(6).fill(0).map((_, index) => (
      <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={`skeleton-${index}`}>
        <Skeleton 
          variant="rounded" 
          height={320} 
          animation="wave" 
          sx={{ borderRadius: 4 }}
        />
      </Grid>
    ));
  };

  // Staggered animation for cards
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  return (
    <Container maxWidth="xl" sx={{ width: '100%' }}>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ width: '100%' }}
      >
        <Box sx={{ mb: 5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography 
            variant="h3" 
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
            Personas
          </Typography>
          
          <Button
            variant="contained"
            color="secondary"
            startIcon={<AddIcon />}
            onClick={handleCreatePersona}
            sx={{
              borderRadius: '28px',
              px: 3,
              py: 1.2,
              boxShadow: theme.shadows[3],
              '&:hover': {
                transform: 'translateY(-3px)',
                boxShadow: theme.shadows[6],
              },
              transition: 'all 0.3s',
              fontSize: '1rem',
            }}
          >
            Create New
          </Button>
        </Box>
        
        <Box sx={{ mb: 5, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <TextField
            placeholder="Search personas..."
            value={searchTerm}
            onChange={handleSearch}
            sx={{ 
              flexGrow: { xs: 1, md: 1 },
              '& .MuiOutlinedInput-root': {
                borderRadius: '28px',
                backgroundColor: 'white'
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
            }}
          />
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant={sortBy === 'name' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => handleSort('name')}
              color="primary"
              sx={{ borderRadius: '20px' }}
              startIcon={sortBy === 'name' && <SortIcon fontSize="small" />}
            >
              Name
            </Button>
            <Button
              variant={sortBy === 'newest' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => handleSort('newest')}
              color="primary"
              sx={{ borderRadius: '20px' }}
              startIcon={sortBy === 'newest' && <SortIcon fontSize="small" />}
            >
              Newest
            </Button>
            <Button
              variant={sortBy === 'updated' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => handleSort('updated')}
              color="primary"
              sx={{ borderRadius: '20px' }}
              startIcon={sortBy === 'updated' && <SortIcon fontSize="small" />}
            >
              Updated
            </Button>
          </Box>
        </Box>
        
        {error && (
          <Fade in={!!error}>
            <Alert 
              severity="error" 
              sx={{ mb: 3, borderRadius: 2 }}
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          </Fade>
        )}
        
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          style={{ width: '100%' }}
        >
          <Grid container spacing={3}>
            {loading ? (
              renderSkeletons()
            ) : filteredPersonas.length > 0 ? (
              filteredPersonas.map((persona) => (
                <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={persona.id}>
                  <PersonaCard persona={persona} />
                </Grid>
              ))
            ) : (
              <Grid size={{ xs: 12 }}>
                <Box 
                  sx={{ 
                    py: 10, 
                    textAlign: 'center', 
                    backgroundColor: 'rgba(0,0,0,0.02)',
                    borderRadius: 4,
                    border: '1px dashed rgba(0,0,0,0.1)',
                  }}
                >
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    No personas found
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    {searchTerm ? 'Try a different search term' : 'Get started by creating a new persona'}
                  </Typography>
                  {!searchTerm && (
                    <Button
                      variant="contained"
                      onClick={handleCreatePersona}
                      startIcon={<AddIcon />}
                    >
                      Create New Persona
                    </Button>
                  )}
                </Box>
              </Grid>
            )}
          </Grid>
        </motion.div>
      </motion.div>
    </Container>
  );
}

export default PersonaList; 