'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <h1 className="text-2xl font-semibold mb-2">Something went wrong</h1>
      <p className="text-sm text-gray-600 mb-4">
        {error?.message || 'An unexpected error occurred.'}
      </p>
      <button
        className="px-4 py-2 rounded bg-indigo-600 text-white"
        onClick={() => reset()}
      >
        Try again
      </button>
    </div>
  );
}