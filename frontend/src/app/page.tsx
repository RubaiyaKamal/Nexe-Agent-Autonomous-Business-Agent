export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">Nexe Agent</h1>
        <p className="mt-2 text-gray-500">Autonomous Business Agent Dashboard</p>
        <a href="/goals" className="mt-6 inline-block px-6 py-2 bg-blue-600 text-white rounded">
          Go to Goals
        </a>
      </div>
    </main>
  );
}
