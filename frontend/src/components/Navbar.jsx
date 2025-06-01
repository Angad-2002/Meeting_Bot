import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  Box, 
  IconButton, 
  Drawer, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemIcon, 
  useMediaQuery, 
  Avatar, 
  Container,
  useTheme
} from '@mui/material';
import { 
  Menu as MenuIcon, 
  ChevronRight as ChevronRightIcon,
  Person as PersonIcon,
  PlayArrow as PlayArrowIcon,
  Language as LanguageIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const navItems = [
  { title: 'Personas', path: '/', icon: <PersonIcon /> },
  { title: 'Create Bot', path: '/bots', icon: <PlayArrowIcon /> },
  { title: 'Active Bots', path: '/active-bots', icon: <LanguageIcon /> },
];

function Navbar() {
  const theme = useTheme();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  useEffect(() => {
    const handleScroll = () => {
      const isScrolled = window.scrollY > 10;
      if (isScrolled !== scrolled) {
        setScrolled(isScrolled);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [scrolled]);

  const toggleDrawer = (open) => (event) => {
    if (
      event.type === 'keydown' &&
      (event.key === 'Tab' || event.key === 'Shift')
    ) {
      return;
    }
    setDrawerOpen(open);
  };

  return (
    <AppBar 
      position="sticky" 
      elevation={scrolled ? 4 : 0} 
      color="inherit"
      sx={{
        backgroundColor: scrolled ? 'rgba(255, 255, 255, 0.95)' : 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(8px)',
        transition: 'all 0.3s ease-out',
        borderBottom: scrolled 
          ? `1px solid ${theme.palette.grey[200]}` 
          : 'none',
      }}
    >
      <Container maxWidth="xl">
        <Toolbar disableGutters>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Typography
              variant="h6"
              component={Link}
              to="/"
              sx={{
                mr: 2,
                display: 'flex',
                alignItems: 'center',
                fontWeight: 700,
                letterSpacing: '.2rem',
                color: theme.palette.primary.main,
                textDecoration: 'none',
                flexGrow: { xs: 1, md: 0 },
              }}
            >
              <Avatar 
                src="/bot-logo.png" 
                alt="Meeting Bot" 
                sx={{ mr: 1, width: 32, height: 32, backgroundColor: theme.palette.primary.light }}
              >
                MB
              </Avatar>
              {!isMobile && 'MEETING BOT'}
            </Typography>
          </motion.div>

          {isMobile ? (
            <>
              <Box sx={{ flexGrow: 1 }} />
              <IconButton
                color="inherit"
                aria-label="open drawer"
                edge="start"
                onClick={toggleDrawer(true)}
              >
                <MenuIcon />
              </IconButton>
              <Drawer
                anchor="right"
                open={drawerOpen}
                onClose={toggleDrawer(false)}
                sx={{
                  '& .MuiDrawer-paper': {
                    width: 280,
                    boxSizing: 'border-box',
                    borderRadius: '16px 0 0 16px',
                  },
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 2,
                    backgroundColor: theme.palette.primary.main,
                    color: 'white',
                  }}
                >
                  <Typography variant="h6">Menu</Typography>
                  <IconButton onClick={toggleDrawer(false)} sx={{ color: 'white' }}>
                    <ChevronRightIcon />
                  </IconButton>
                </Box>

                <List>
                  {navItems.map((item) => (
                    <ListItem
                      component={Link}
                      to={item.path}
                      onClick={toggleDrawer(false)}
                      selected={location.pathname === item.path}
                      sx={{
                        backgroundColor: location.pathname === item.path 
                          ? theme.palette.primary.light + '20' 
                          : 'transparent',
                        borderRight: location.pathname === item.path 
                          ? `4px solid ${theme.palette.primary.main}` 
                          : 'none',
                        '&:hover': {
                          backgroundColor: theme.palette.primary.light + '10',
                        },
                      }}
                      key={item.title}
                    >
                      <ListItemIcon 
                        sx={{ 
                          color: location.pathname === item.path 
                            ? theme.palette.primary.main 
                            : theme.palette.text.primary 
                        }}
                      >
                        {item.icon}
                      </ListItemIcon>
                      <ListItemText primary={item.title} />
                    </ListItem>
                  ))}
                </List>
              </Drawer>
            </>
          ) : (
            <Box 
              sx={{ 
                flexGrow: 1, 
                display: 'flex', 
                justifyContent: 'center', 
                ml: 4 
              }}
            >
              {navItems.map((item, index) => (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <Button
                    component={Link}
                    to={item.path}
                    color={location.pathname === item.path ? 'primary' : 'inherit'}
                    sx={{
                      mx: 1,
                      position: 'relative',
                      fontWeight: location.pathname === item.path ? 600 : 400,
                      '&::after': {
                        content: '""',
                        position: 'absolute',
                        width: location.pathname === item.path ? '60%' : '0%',
                        height: '3px',
                        bottom: '6px',
                        left: '20%',
                        backgroundColor: theme.palette.primary.main,
                        transition: 'all 0.3s ease',
                        borderRadius: '3px',
                      },
                      '&:hover::after': {
                        width: '60%',
                      },
                    }}
                    startIcon={item.icon}
                  >
                    {item.title}
                  </Button>
                </motion.div>
              ))}
            </Box>
          )}
          
          {!isMobile && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
            >
              <Button
                component={Link}
                to="/personas/new"
                variant="contained"
                color="primary"
                sx={{
                  borderRadius: '20px',
                  px: 3,
                  '&:hover': {
                    transform: 'translateY(-3px)',
                  },
                  transition: 'transform 0.3s ease',
                }}
              >
                Create New Persona
              </Button>
            </motion.div>
          )}
        </Toolbar>
      </Container>
    </AppBar>
  );
}

export default Navbar; 