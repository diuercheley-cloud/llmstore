import React from 'react';

const DAGValidatorPanel: React.FC<{ errors: any[] }> = ({ errors }) => {
  return (
    <div className="p-4 border-b">
      <h3 className="text-sm font-bold uppercase text-gray-500 mb-2">DAG Validator</h3>
      {errors.length === 0 ? (
        <div className="text-green-600 text-sm">✓ Flow is valid</div>
      ) : (
        <div className="space-y-1">
          {errors.map((err, i) => (
            <div key={i} className="text-red-500 text-xs font-medium">• {err.message}</div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DAGValidatorPanel;
