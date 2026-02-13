/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      { source: '/story/:id', destination: '/topic/:id', permanent: true },
      { source: '/how-it-works', destination: '/methodology', permanent: true },
    ];
  },
};

module.exports = nextConfig;
