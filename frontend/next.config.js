/** @type {import('next').NextConfig} */

/**
 * CDN Configuration for ResuBoost AI
 *
 * Environment Variables:
 * - NEXT_PUBLIC_CDN_URL: CDN base URL (e.g., https://cdn.example.com)
 * - NEXT_PUBLIC_ASSET_PREFIX: Asset prefix for CDN (defaults to CDN_URL)
 * - NODE_ENV: Environment (development, staging, production)
 */

const cdnUrl = process.env.NEXT_PUBLIC_CDN_URL || ''
const assetPrefix = process.env.NEXT_PUBLIC_ASSET_PREFIX || cdnUrl

// CDN domains for image optimization
const cdnDomains = [
  'cdn.resuboost.ai',
  'assets.resuboost.ai',
  'd1234567890.cloudfront.net', // AWS CloudFront example
  'resuboost.pages.dev', // Cloudflare Pages
].filter(Boolean)

// Additional image domains from environment
const additionalImageDomains = process.env.NEXT_PUBLIC_IMAGE_DOMAINS
  ? process.env.NEXT_PUBLIC_IMAGE_DOMAINS.split(',').map(d => d.trim())
  : []

const nextConfig = {
  output: 'standalone',

  // CDN Asset Prefix - serves static assets from CDN in production
  assetPrefix: process.env.NODE_ENV === 'production' ? assetPrefix : undefined,

  // Compress responses
  compress: true,

  // Generate ETags for caching
  generateEtags: true,

  // Powered by header (disable for security)
  poweredByHeader: false,

  // Strict mode for React
  reactStrictMode: true,

  env: {
    API_URL: process.env.API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_CDN_URL: cdnUrl,
  },

  // Image optimization configuration
  images: {
    // Use Sharp for image optimization (better performance)
    // Sharp is auto-detected when installed

    // Output formats - prefer modern formats
    formats: ['image/avif', 'image/webp'],

    // Device sizes for responsive images
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],

    // Image sizes for next/image with sizes prop
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],

    // Minimum cache TTL in seconds (30 days)
    minimumCacheTTL: 2592000,

    // Disable static image imports optimization in development for faster builds
    disableStaticImages: process.env.NODE_ENV === 'development',

    // Remote patterns for CDN and external images
    remotePatterns: [
      // CDN domains
      ...cdnDomains.map(hostname => ({
        protocol: 'https',
        hostname,
        port: '',
        pathname: '/**',
      })),
      // Additional configured domains
      ...additionalImageDomains.map(hostname => ({
        protocol: 'https',
        hostname,
        port: '',
        pathname: '/**',
      })),
      // Allow localhost in development
      ...(process.env.NODE_ENV === 'development' ? [{
        protocol: 'http',
        hostname: 'localhost',
        port: '3000',
        pathname: '/**',
      }] : []),
    ],

    // Use CDN loader in production
    loader: process.env.NODE_ENV === 'production' && cdnUrl ? 'custom' : 'default',
    loaderFile: process.env.NODE_ENV === 'production' && cdnUrl ? './src/lib/cdn-image-loader.js' : undefined,
  },

  // HTTP headers for caching and security
  async headers() {
    return [
      // Static assets - long cache (1 year)
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
        ],
      },
      // Images - 30 days cache
      {
        source: '/images/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=2592000, stale-while-revalidate=86400',
          },
        ],
      },
      // Optimized images from Next.js
      {
        source: '/_next/image/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=2592000, stale-while-revalidate=86400',
          },
        ],
      },
      // Fonts - long cache
      {
        source: '/fonts/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
          {
            key: 'Access-Control-Allow-Origin',
            value: '*',
          },
        ],
      },
      // HTML pages - no cache or short TTL
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
      // API responses - vary by auth
      {
        source: '/api/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'private, no-cache, no-store, must-revalidate',
          },
          {
            key: 'Vary',
            value: 'Authorization, Accept-Encoding',
          },
        ],
      },
      // Service worker - no cache
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
      // Manifest - short cache
      {
        source: '/manifest.json',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=86400',
          },
          {
            key: 'Content-Type',
            value: 'application/manifest+json',
          },
        ],
      },
    ]
  },

  // Rewrites for CDN fallback
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [
        // Fallback for CDN assets to origin
        ...(cdnUrl ? [{
          source: '/cdn-assets/:path*',
          destination: `${cdnUrl}/:path*`,
        }] : []),
      ],
      fallback: [],
    }
  },

  // Webpack configuration for optimization
  webpack: (config, { dev, isServer }) => {
    // Production optimizations
    if (!dev && !isServer) {
      // Enable module concatenation
      config.optimization.concatenateModules = true

      // Split chunks for better caching
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          ...config.optimization.splitChunks?.cacheGroups,
          // Vendor chunk for node_modules
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
            priority: 10,
          },
          // Common chunk for shared code
          common: {
            minChunks: 2,
            chunks: 'all',
            name: 'common',
            priority: 5,
            reuseExistingChunk: true,
          },
        },
      }
    }

    return config
  },

  // Experimental features for performance
  experimental: {
    // Optimize package imports
    optimizePackageImports: [
      'lucide-react',
      '@dnd-kit/core',
      '@dnd-kit/sortable',
      '@dnd-kit/utilities',
    ],
  },
}

module.exports = nextConfig
