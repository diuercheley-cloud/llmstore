import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const PromptPreview: React.FC<{ prompt?: string }> = ({ prompt }) => (
  <Box sx={{ p: 2 }}>
    <Typography variant="overline">Prompt Preview</Typography>
    <Paper variant="outlined" sx={{ p: 1, bgcolor: 'grey.50', fontFamily: 'monospace', fontSize: '0.8rem' }}>
      {prompt || "You are an agent...\nUser: help me with..."}
    </Paper>
  </Box>
);

export default PromptPreview;
