import { Link } from 'react-router-dom';

import { Card, CardTitle, Muted } from '@/components/ui';

export default function NotFoundPage() {
  return (
    <Card>
      <CardTitle>Page not found</CardTitle>
      <Muted>The page you requested doesn’t exist.</Muted>
      <div className="mt-4">
        <Link to="/" className="text-sm font-semibold text-primary hover:underline">
          Go home
        </Link>
      </div>
    </Card>
  );
}
