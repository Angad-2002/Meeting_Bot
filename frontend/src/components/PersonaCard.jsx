import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  CardContent, 
  CardMedia, 
  Typography, 
  Box, 
  Chip, 
  IconButton, 
  Tooltip, 
  Skeleton,
  Collapse
} from '@mui/material';
import { motion } from 'framer-motion';
import EditIcon from '@mui/icons-material/Edit';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

function PersonaCard({ persona, onClick }) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(!!persona.image);

  const handleEditClick = (e) => {
    e.stopPropagation();
    navigate(`/personas/${persona.id}`);
  };

  const handlePlayClick = (e) => {
    e.stopPropagation();
    navigate(`/bots?persona=${persona.id}`);
  };

  const toggleExpand = (e) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  // Truncate long text
  const truncate = (text, length = 100) => {
    if (!text) return '';
    return text.length > length ? `${text.substring(0, length)}...` : text;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      whileHover={{ y: -8 }}
    >
      <Card 
        sx={{ 
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          cursor: 'pointer',
          overflow: 'visible',
          position: 'relative',
          borderRadius: 4,
          boxShadow: (theme) => theme.shadows[2],
          '&:hover': {
            boxShadow: (theme) => theme.shadows[6],
          },
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
        onClick={onClick || (() => navigate(`/personas/${persona.id}`))}
      >
        {/* Card Actions Float Buttons */}
        <Box 
          sx={{ 
            position: 'absolute', 
            top: 10, 
            right: 10, 
            zIndex: 1,
            display: 'flex',
            gap: 1,
          }}
        >
          <Tooltip title="Edit Persona">
            <IconButton 
              size="small" 
              onClick={handleEditClick}
              sx={{ 
                bgcolor: 'background.paper', 
                boxShadow: 2,
                '&:hover': { 
                  bgcolor: 'primary.light',
                  color: 'white',
                },
              }}
            >
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Create Bot with this Persona">
            <IconButton 
              size="small" 
              color="primary"
              onClick={handlePlayClick}
              sx={{ 
                bgcolor: 'background.paper', 
                boxShadow: 2,
                '&:hover': { 
                  bgcolor: 'secondary.main',
                  color: 'white',
                },
              }}
            >
              <PlayArrowIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        
        {/* Card Image */}
        {persona.image ? (
          <>
            {!imageLoaded && (
              <Skeleton 
                variant="rectangular" 
                height={200} 
                animation="wave"
                sx={{ borderTopLeftRadius: 16, borderTopRightRadius: 16 }}
              />
            )}
            <CardMedia
              component="img"
              height={200}
              image={persona.image}
              alt={persona.name}
              onLoad={() => setImageLoaded(true)}
              sx={{ 
                display: imageLoaded ? 'block' : 'none',
                objectFit: 'cover',
                borderTopLeftRadius: 16, 
                borderTopRightRadius: 16 
              }}
            />
          </>
        ) : (
          <Box 
            sx={{ 
              height: 140, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              backgroundImage: (theme) => 
                `linear-gradient(135deg, ${theme.palette.primary.light} 0%, ${theme.palette.secondary.light} 100%)`,
              borderTopLeftRadius: 16, 
              borderTopRightRadius: 16,
              color: 'white',
              fontSize: '3rem',
              fontWeight: 'bold',
            }}
          >
            {persona.name?.charAt(0) || '?'}
          </Box>
        )}
        
        {/* Card Content */}
        <CardContent sx={{ flexGrow: 1, p: 3 }}>
          <Typography 
            variant="h6" 
            gutterBottom
            sx={{ 
              fontWeight: 600,
              color: 'primary.main',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {persona.name}
          </Typography>
          
          <Typography 
            variant="body2" 
            color="text.secondary" 
            sx={{ 
              mb: 2,
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitLineClamp: expanded ? 'unset' : 3,
              WebkitBoxOrient: 'vertical',
            }}
          >
            {expanded ? persona.description : truncate(persona.description, 150)}
          </Typography>
          
          <Collapse in={expanded} timeout="auto" unmountOnExit>
            {persona.personality && (
              <Box mb={2}>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  Personality:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {persona.personality}
                </Typography>
              </Box>
            )}
            
            {persona.knowledge_base && (
              <Box mb={2}>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  Knowledge Base:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {persona.knowledge_base}
                </Typography>
              </Box>
            )}
          </Collapse>
          
          {/* Expand/Collapse Control */}
          {persona.description?.length > 150 && (
            <Box 
              sx={{ 
                display: 'flex', 
                justifyContent: 'center', 
                mt: 1,
                mb: expanded ? 2 : 0
              }}
            >
              <IconButton 
                size="small" 
                onClick={toggleExpand} 
                sx={{ 
                  bgcolor: 'grey.100',
                  '&:hover': {
                    bgcolor: 'grey.200',
                  },
                }}
              >
                {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
          )}
          
          {/* Tags */}
          {persona.characteristics && persona.characteristics.length > 0 && (
            <Box mt={1} sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {persona.characteristics.map((char, index) => (
                <Chip
                  key={index}
                  label={char}
                  size="small"
                  sx={{ 
                    borderRadius: '16px',
                    bgcolor: (theme) => `${theme.palette.primary.main}10`,
                    color: 'primary.dark',
                    fontWeight: 500,
                    mb: 0.5,
                  }}
                />
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default PersonaCard; 