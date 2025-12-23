import type { Meta, StoryObj } from '@storybook/react-vite';
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardContent,
  CardFooter
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const meta = {
  title: 'UI/Card',
  component: Card,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
        <CardDescription>Card Description</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Card content goes here.</p>
      </CardContent>
    </Card>
  ),
};

export const WithFooter: Story = {
  render: () => (
    <Card className="w-[350px]">
      <CardHeader>
        <CardTitle>Card with Footer</CardTitle>
        <CardDescription>This card has a footer with actions.</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Some content here.</p>
      </CardContent>
      <CardFooter>
        <Button variant="outline">Cancel</Button>
        <Button className="ml-2">Save</Button>
      </CardFooter>
    </Card>
  ),
};

// Research-specific cards
export const ResearchPaper: Story = {
  render: () => (
    <Card className="w-[400px]">
      <CardHeader>
        <div className="flex justify-between items-start">
          <CardTitle>R&D Investment Intensity</CardTitle>
          <Badge variant="outline">Pre-print</Badge>
        </div>
        <CardDescription>
          A Quintile Portfolio Analysis of Stock Returns (2005-2024)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          This paper examines the relationship between R&D investment intensity 
          and subsequent stock returns using a quintile portfolio approach.
        </p>
      </CardContent>
      <CardFooter>
        <Button variant="outline" size="sm">Read Paper</Button>
      </CardFooter>
    </Card>
  ),
};

export const StatisticCard: Story = {
  render: () => (
    <Card className="w-[200px]">
      <CardHeader className="pb-2">
        <CardDescription>R&D Premium (Q5 - Q1)</CardDescription>
        <CardTitle className="text-3xl text-emerald-500">+4.2%</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">
          Annualized excess return
        </p>
      </CardContent>
    </Card>
  ),
};

export const QuintileCard: Story = {
  render: () => (
    <Card className="w-[300px]">
      <CardHeader>
        <CardTitle>Quintile 5 (Highest R&D)</CardTitle>
        <CardDescription>Top 20% by R&D Intensity</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Avg R&D Intensity</span>
          <span className="font-medium">18.5%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Avg Return</span>
          <span className="font-medium text-emerald-500">12.3%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Companies</span>
          <span className="font-medium">100</span>
        </div>
      </CardContent>
    </Card>
  ),
};

export const SectorCard: Story = {
  render: () => (
    <Card className="w-[280px]">
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle className="text-lg">Technology</CardTitle>
          <Badge>29.5%</Badge>
        </div>
        <CardDescription>S&P 500 Sector Weight</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Avg R&D Intensity</span>
            <span>14.2%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Companies</span>
            <span>85</span>
          </div>
        </div>
      </CardContent>
    </Card>
  ),
};

