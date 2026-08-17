import "./globals.css";

export const metadata = {
  title: "Video Factory AI",
  description: "Usine vidéo multi-agents free-first",
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
