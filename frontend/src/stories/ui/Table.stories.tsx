import type { Meta, StoryObj } from '@storybook/react-vite';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

const meta = {
  title: 'UI/Table',
  component: Table,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Table>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Amount</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell>John Doe</TableCell>
          <TableCell>Active</TableCell>
          <TableCell>$100.00</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Jane Smith</TableCell>
          <TableCell>Pending</TableCell>
          <TableCell>$250.00</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  ),
};

// Research-specific tables
export const QuintilePerformance: Story = {
  render: () => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Quintile</TableHead>
          <TableHead>R&D Intensity</TableHead>
          <TableHead>Avg Return</TableHead>
          <TableHead>Sharpe</TableHead>
          <TableHead>N</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell>Q1 (Low)</TableCell>
          <TableCell>0.5%</TableCell>
          <TableCell className="text-red-500">6.2%</TableCell>
          <TableCell>0.42</TableCell>
          <TableCell>100</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Q2</TableCell>
          <TableCell>2.1%</TableCell>
          <TableCell>7.8%</TableCell>
          <TableCell>0.51</TableCell>
          <TableCell>100</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Q3</TableCell>
          <TableCell>5.4%</TableCell>
          <TableCell>9.1%</TableCell>
          <TableCell>0.58</TableCell>
          <TableCell>100</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Q4</TableCell>
          <TableCell>9.8%</TableCell>
          <TableCell>10.5%</TableCell>
          <TableCell>0.65</TableCell>
          <TableCell>100</TableCell>
        </TableRow>
        <TableRow className="font-medium">
          <TableCell>Q5 (High)</TableCell>
          <TableCell>18.5%</TableCell>
          <TableCell className="text-emerald-500">12.3%</TableCell>
          <TableCell>0.72</TableCell>
          <TableCell>100</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  ),
};

export const ANOVAResults: Story = {
  render: () => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Window</TableHead>
          <TableHead>F-Statistic</TableHead>
          <TableHead>p-value</TableHead>
          <TableHead>Eta-squared</TableHead>
          <TableHead>Significant</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell>5-Year</TableCell>
          <TableCell>4.52</TableCell>
          <TableCell>&lt; 0.001</TableCell>
          <TableCell>0.08</TableCell>
          <TableCell>
            <Badge variant="default">Yes</Badge>
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell>10-Year</TableCell>
          <TableCell>6.78</TableCell>
          <TableCell>&lt; 0.001</TableCell>
          <TableCell>0.12</TableCell>
          <TableCell>
            <Badge variant="default">Yes</Badge>
          </TableCell>
        </TableRow>
        <TableRow>
          <TableCell>20-Year</TableCell>
          <TableCell>8.94</TableCell>
          <TableCell>&lt; 0.001</TableCell>
          <TableCell>0.15</TableCell>
          <TableCell>
            <Badge variant="default">Yes</Badge>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  ),
};

export const TopRDCompanies: Story = {
  render: () => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Company</TableHead>
          <TableHead>Sector</TableHead>
          <TableHead>R&D Intensity</TableHead>
          <TableHead>Weight</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell className="font-mono">AAPL</TableCell>
          <TableCell>Apple Inc.</TableCell>
          <TableCell>
            <Badge variant="outline">Technology</Badge>
          </TableCell>
          <TableCell>7.2%</TableCell>
          <TableCell>5.0%</TableCell>
        </TableRow>
        <TableRow>
          <TableCell className="font-mono">MSFT</TableCell>
          <TableCell>Microsoft Corp.</TableCell>
          <TableCell>
            <Badge variant="outline">Technology</Badge>
          </TableCell>
          <TableCell>12.8%</TableCell>
          <TableCell>5.0%</TableCell>
        </TableRow>
        <TableRow>
          <TableCell className="font-mono">GILD</TableCell>
          <TableCell>Gilead Sciences</TableCell>
          <TableCell>
            <Badge variant="outline">Healthcare</Badge>
          </TableCell>
          <TableCell>22.5%</TableCell>
          <TableCell>5.0%</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  ),
};

