import { lazy } from 'react'
import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom'
import { MarketingShell } from '@/components/layout/marketing-shell'
import { AppShell } from '@/components/layout/app-shell'
import { RequireAuth, RedirectIfAuthenticated } from './route-guards'
import { featureRoutes } from '@/features/registry'

/*
 * Splitting policy
 * ----------------
 * Eager: the landing page and the auth pages. These are the first paint for
 * almost every visitor, and deferring them would trade a fast entry for a
 * spinner on the one screen where a spinner is most visible.
 *
 * Lazy: everything else. The app pages in particular pull in Recharts and the
 * whole pipeline UI, none of which a signed-out visitor needs.
 *
 * Suspense boundaries live in the two shells, around their <Outlet />.
 */

import LandingPage from '@/pages/marketing/landing'
import LoginPage from '@/pages/auth/login'
import SignupPage from '@/pages/auth/signup'
import ForgotPasswordPage from '@/pages/auth/forgot-password'
import ResetPasswordPage from '@/pages/auth/reset-password'
import NotFoundPage from '@/pages/not-found'

const HowItWorksPage = lazy(() => import('@/pages/marketing/how-it-works'))
const FeaturesPage = lazy(() => import('@/pages/marketing/features'))
const AboutPage = lazy(() => import('@/pages/marketing/about'))
const PricingPage = lazy(() => import('@/pages/marketing/pricing'))
const ContactPage = lazy(() => import('@/pages/marketing/contact'))

const DashboardPage = lazy(() => import('@/pages/app/dashboard'))
const ProjectsPage = lazy(() => import('@/pages/app/projects'))
const NewProjectPage = lazy(() => import('@/pages/app/project-new'))
const PipelinePage = lazy(() => import('@/pages/app/project-pipeline'))
const InsightsPage = lazy(() => import('@/pages/app/project-insights'))
const ReviewGapsPage = lazy(() => import('@/pages/app/project-review-gaps'))
const StrategyPage = lazy(() => import('@/pages/app/project-strategy'))
const ReviewStrategyPage = lazy(() => import('@/pages/app/project-review-strategy'))
const DocumentPage = lazy(() => import('@/pages/app/project-document'))
const AutomationPage = lazy(() => import('@/pages/app/project-automation'))
const ProfileSettingsPage = lazy(() => import('@/pages/app/settings-profile'))
const AccountSettingsPage = lazy(() => import('@/pages/app/settings-account'))
const IntegrationsSettingsPage = lazy(() => import('@/pages/app/settings-integrations'))
const BillingSettingsPage = lazy(() => import('@/pages/app/settings-billing'))

/**
 * Routes are declared here only. Teammates' features are mounted from the
 * registry at the bottom rather than being added to this list by hand. See
 * src/features/registry.ts and docs/architecture.md.
 *
 * Exported separately from `router` so tests can mount the same table on a
 * memory router and actually navigate it.
 */
export const routes: RouteObject[] = [
  {
    element: <MarketingShell />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/how-it-works', element: <HowItWorksPage /> },
      { path: '/features', element: <FeaturesPage /> },
      { path: '/about', element: <AboutPage /> },
      { path: '/pricing', element: <PricingPage /> },
      { path: '/contact', element: <ContactPage /> },
    ],
  },
  {
    element: <RedirectIfAuthenticated />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
    ],
  },
  // Reachable while signed in: Supabase drops the user here after the reset link.
  { path: '/reset-password', element: <ResetPasswordPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        path: '/app',
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="/app/dashboard" replace /> },
          {
            path: 'dashboard',
            element: <DashboardPage />,
            handle: { crumb: 'Dashboard' },
          },
          {
            path: 'projects',
            handle: { crumb: 'Projects' },
            children: [
              { index: true, element: <ProjectsPage /> },
              { path: 'new', element: <NewProjectPage />, handle: { crumb: 'New analysis' } },
              {
                path: ':projectId',
                children: [
                  { index: true, element: <Navigate to="pipeline" replace /> },
                  {
                    path: 'pipeline',
                    element: <PipelinePage />,
                    handle: { crumb: 'Pipeline' },
                  },
                  {
                    path: 'insights',
                    element: <InsightsPage />,
                    handle: { crumb: 'Insights' },
                  },
                  {
                    path: 'review-gaps',
                    element: <ReviewGapsPage />,
                    handle: { crumb: 'Review gaps' },
                  },
                  {
                    path: 'strategy',
                    element: <StrategyPage />,
                    handle: { crumb: 'Strategy' },
                  },
                  {
                    path: 'review-strategy',
                    element: <ReviewStrategyPage />,
                    handle: { crumb: 'Final approval' },
                  },
                  {
                    path: 'document',
                    element: <DocumentPage />,
                    handle: { crumb: 'Document' },
                  },
                  {
                    path: 'automation',
                    element: <AutomationPage />,
                    handle: { crumb: 'Automation' },
                  },
                ],
              },
            ],
          },
          {
            path: 'settings',
            handle: { crumb: 'Settings' },
            children: [
              { index: true, element: <Navigate to="profile" replace /> },
              {
                path: 'profile',
                element: <ProfileSettingsPage />,
                handle: { crumb: 'Profile' },
              },
              {
                path: 'account',
                element: <AccountSettingsPage />,
                handle: { crumb: 'Account' },
              },
              {
                path: 'integrations',
                element: <IntegrationsSettingsPage />,
                handle: { crumb: 'Integrations' },
              },
              {
                path: 'billing',
                element: <BillingSettingsPage />,
                handle: { crumb: 'Billing' },
              },
            ],
          },
          // Teammates' registered features mount here, one entry each.
          ...featureRoutes().map((route) => ({
            path: route.path,
            element: <route.component />,
            handle: { crumb: route.featureKey },
          })),
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]

export const router = createBrowserRouter(routes)
