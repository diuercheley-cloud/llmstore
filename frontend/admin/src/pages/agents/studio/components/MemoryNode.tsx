import React from 'react';
import { Paper, Typography } from '@mui/material';
import { Storage as MemoryIcon } from '@mui/icons-material';

const MemoryNode: React.FC<{ label?: string }> = ({ label }) => (
  <Paper sx={{ p: 1, minWidth: 120, border: 1, borderColor: 'info.light', display: 'flex', alignItems: 'center' }}>
    <MemoryIcon sx={{ mr: 1, color: 'info.main' }} />
    <Typography variant="body2">{label || 'Memory'}</Typography>
  </Paper>
);

export default MemoryNode;
