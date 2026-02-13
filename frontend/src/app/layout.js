import './globals.css';
import NavBar from '../components/NavBar';
import Footer from '../components/Footer';

export const metadata = {
  title: 'ClearSignal — Same Event. Different Realities.',
  description: 'See how 100+ news sources across the political spectrum frame the same stories differently. Coverage analysis powered by AI.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;800;900&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body suppressHydrationWarning>
        <NavBar />
        {children}
        <Footer />
      </body>
    </html>
  );
}
