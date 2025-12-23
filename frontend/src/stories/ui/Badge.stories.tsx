import type { Meta, StoryObj } from '@storybook/react-vite';
import { Badge } from '@/components/ui/badge';

const meta = {
  title: 'UI/Badge',
  component: Badge,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'secondary', 'destructive', 'outline'],
    },
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    children: 'Badge',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    children: 'Secondary',
  },
};

export const Destructive: Story = {
  args: {
    variant: 'destructive',
    children: 'Destructive',
  },
};

export const Outline: Story = {
  args: {
    variant: 'outline',
    children: 'Outline',
  },
};

// Research-specific badges
export const PrePrint: Story = {
  args: {
    variant: 'outline',
    children: 'Pre-print',
  },
};

export const HighRD: Story = {
  args: {
    variant: 'default',
    children: 'High R&D',
  },
};

export const PValue: Story = {
  args: {
    variant: 'secondary',
    children: 'p < 0.001',
  },
};

export const Sector: Story = {
  args: {
    variant: 'outline',
    children: 'Technology',
  },
};

