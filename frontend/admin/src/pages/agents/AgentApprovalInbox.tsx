import React from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableHead, TableRow, Paper, Button } from '@mui/material';

export const AgentApprovalInbox: React.FC = () => {
    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>Approval Inbox</Typography>
            <Paper sx={{ p: 2 }}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Request</TableCell>
                            <TableCell>Risk</TableCell>
                            <TableCell>Expires In</TableCell>
                            <TableCell>Action</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        <TableRow>
                            <TableCell>Execute destructive tool: <code>db.delete_record</code></TableCell>
                            <TableCell><Typography color="error.main">High</Typography></TableCell>
                            <TableCell>12 mins</TableCell>
                            <TableCell>
                                <Button size="small" variant="contained" color="success" sx={{ mr: 1 }}>Approve</Button>
                                <Button size="small" variant="outlined" color="error">Reject</Button>
                            </TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </Paper>
        </Box>
    );
};

export default AgentApprovalInbox;
