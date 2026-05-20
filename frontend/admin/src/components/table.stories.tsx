import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./button";
import { Badge } from "./badge";
import { Table } from "./table";
import tableHistory from "../stories/history/table.md?raw";

type ReleaseRow = {
  id: string;
  service: string;
  status: string;
  latency: string;
};

const rows: ReleaseRow[] = [
  { id: "rel-198", service: "gateway", status: "healthy", latency: "182 ms" },
  { id: "rel-199", service: "router", status: "warning", latency: "420 ms" },
  { id: "rel-200", service: "embeddings", status: "degraded", latency: "691 ms" },
];

const meta = {
  component: Table<ReleaseRow>,
  tags: ["ai-generated", "autodocs"],
  args: {
    caption: "Tabela de releases monitoradas",
    data: rows,
    columns: [
      { key: "service", header: "Service" },
      {
        key: "status",
        header: "Status",
        render: (row: ReleaseRow) => (
          <Badge tone={row.status === "healthy" ? "success" : row.status === "warning" ? "warning" : "danger"}>
            {row.status}
          </Badge>
        ),
      },
      { key: "latency", header: "P95", align: "right" },
      {
        key: "actions",
        header: "Actions",
        align: "right",
        render: () => (
          <Button size="sm" variant="outline">
            Open
          </Button>
        ),
      },
    ],
  },
  parameters: {
    docs: {
      description: {
        component:
          "Tabela presentacional reutilizável para conjuntos de dados pequenos e médios, com estados tipados para loading, erro, vazio e bloqueio de interação.\n\n## Histórico de mudanças\n" +
          tableHistory,
      },
    },
  },
} satisfies Meta<typeof Table<ReleaseRow>>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const States: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="space-y-6">
      <Table columns={meta.args.columns} data={rows} />
      <Table columns={meta.args.columns} data={[]} isLoading />
      <Table columns={meta.args.columns} data={[]} error="API de releases indisponível no momento." />
      <Table columns={meta.args.columns} data={rows} isDisabled />
      <div className="rounded-3xl border border-border p-4">
        <p className="mb-3 text-sm font-semibold text-muted-foreground">Hover e focus são revisados nas linhas e ações internas.</p>
        <Table columns={meta.args.columns} data={rows.slice(0, 1)} />
      </div>
    </div>
  ),
};

export const Variants: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="space-y-6">
      <Table columns={meta.args.columns} data={rows} caption="Tabela compacta" />
      <Table columns={meta.args.columns.slice(0, 3)} data={rows} caption="Tabela resumida" />
    </div>
  ),
};

export const Usage: Story = {
  parameters: {
    docs: {
      source: {
        code: `import { Badge } from "@/components/badge";
import { Button } from "@/components/button";
import { Table } from "@/components/table";

<Table
  caption="Backends monitorados"
  data={backends}
  columns={[
    { key: "name", header: "Backend" },
    {
      key: "status",
      header: "Status",
      render: (row) => <Badge tone={row.isHealthy ? "success" : "danger"}>{row.status}</Badge>,
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: () => <Button size="sm" variant="outline">Diagnose</Button>,
    },
  ]}
/>`,
      },
    },
  },
};
