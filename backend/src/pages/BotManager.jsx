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
} from '@mui/material';
import { motion } from 'framer-motion';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SettingsIcon from '@mui/icons-material/Settings';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import PublicIcon from '@mui/icons-material/Public';
import apiService from '../services/api';

// ... rest of the file 