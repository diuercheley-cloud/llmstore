import React from 'react';
import { Box, Typography, Chip } from '@mui/material';

const PolicyDecisionViewer: React.FC = () => (
  <Box sx={{ p: 2 }}>
    <Typography variant="overline">Policy Decision</Typography>
    <Box sx={{ mt: 1 }}>
      <Chip label="ALLOW" color="success" size="small" />
      <Typography variant="caption" display="block" sx={{ mt: 1 }}>
        Reason: Tool 'list_files' is in the allowlist for this tenant.
      </Typography>
    </Box>
  </Box>
);

export default PolicyDecisionViewer;
