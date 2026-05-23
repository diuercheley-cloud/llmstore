import React from 'react';
import { Box, Paper, Typography, Grid } from '@mui/material';
import NodePalette from './NodePalette';

const FlowBuilder: React.FC = () => {
  return (
    <Grid container sx={{ height: '100%' }}>
      <Grid item xs={2} sx={{ borderRight: 1, borderColor: 'divider', bgcolor: 'background.default' }}>
        <NodePalette />
      </Grid>
      <Grid item xs={10} sx={{ position: 'relative', overflow: 'auto', p: 2 }}>
        <Box sx={{ 
          width: '2000px', 
          height: '2000px', 
          backgroundImage: 'radial-gradient(#ccc 1px, transparent 0)', 
          backgroundSize: '24px 24px' 
        }}>
          {/* Node instances would be rendered here */}
          <Paper sx={{ 
            p: 2, 
            width: 150, 
            position: 'absolute', 
            top: 100, 
            left: 100, 
            border: 2, 
            borderColor: 'primary.main' 
          }}>
            <Typography variant="subtitle2">Start Node</Typography>
          </Paper>
          
          <Box sx={{ 
            position: 'absolute', 
            top: 135, 
            left: 250, 
            width: 100, 
            height: 2, 
            bgcolor: 'text.secondary' 
          }} />

          <Paper sx={{ 
            p: 2, 
            width: 150, 
            position: 'absolute', 
            top: 100, 
            left: 350, 
            border: 1, 
            borderColor: 'divider' 
          }}>
            <Typography variant="subtitle2">Agent Node</Typography>
          </Paper>
        </Box>
      </Grid>
    </Grid>
  );
};

export default FlowBuilder;
