import React from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';

const ContextWindowViewer: React.FC = () => (
  <Box sx={{ p: 2 }}>
    <Typography variant="overline">Context Window Usage</Typography>
    <Box sx={{ mt: 1 }}>
      <LinearProgress variant="determinate" value={65} sx={{ height: 10, borderRadius: 5 }} />
      <Typography variant="caption">6500 / 10000 tokens (65%)</Typography>
    </Box>
  </Box>
);

export default ContextWindowViewer;
