/** Management areas backed by real admin API resources. */
export const resourceConfig = {
  projects: { title: 'Projects', description: 'Analyses created by users, including their type, owner and progress.', columns: ['brand_name', 'comparison_type', 'status', 'owner_id', 'updated_at'], filter: 'status', edit: ['brand_name', 'status'] },
  competitors: { title: 'Competitors', description: 'Competitor profiles attached to user projects.', columns: ['name', 'landing_page_url', 'project_id', 'created_at'], edit: ['name', 'notes'] },
  sources: { title: 'Sources', description: 'Pages and listings collected during scraping.', columns: ['title', 'kind', 'status', 'project_id', 'scraped_at'], filter: 'status', edit: ['title', 'status'] },
  products: { title: 'Products', description: 'Marketplace products collected for comparisons.', columns: ['product_name', 'role', 'url', 'project_id', 'scraped_at'], filter: 'role', edit: ['product_name'] },
  'website-pages': { title: 'Website pages', description: 'Pages gathered by the website crawler.', columns: ['title', 'role', 'page_url', 'depth', 'project_id'], filter: 'role', edit: ['title'] },
  'instagram-posts': { title: 'Instagram posts', description: 'Posts gathered from the connected actor.', columns: ['caption', 'role', 'post_url', 'posted_at', 'project_id'], filter: 'role', edit: ['caption'] },
  gaps: { title: 'Gaps', description: 'Opportunities and human review decisions.', columns: ['title', 'category', 'decision', 'user_priority', 'project_id'], filter: 'decision', edit: ['title', 'decision', 'user_priority'] },
  strategies: { title: 'Strategies', description: 'Generated strategies and their approval status.', columns: ['title', 'status', 'generated_at', 'project_id'], filter: 'status', edit: ['title', 'status'] },
  reviews: { title: 'Reviews', description: 'Immutable human checkpoint decisions.', columns: ['stage', 'decision', 'created_at', 'project_id'], filter: 'decision', edit: [] },
  documents: { title: 'Documents', description: 'Strategy documents produced by the pipeline.', columns: ['title', 'generated_at', 'project_id'], edit: ['title'] },
  suggestions: { title: 'Suggestions', description: 'Content ideas generated from approved strategies.', columns: ['title', 'status', 'created_at', 'project_id'], filter: 'status', edit: ['title', 'status'] },
  integrations: { title: 'Integrations', description: 'Feature connections registered by users.', columns: ['name', 'feature_key', 'status', 'owner_id'], filter: 'status', edit: ['name', 'status'] },
  contacts: { title: 'Contact messages', description: 'Messages sent through the public contact form.', columns: ['name', 'email', 'organisation', 'created_at'], edit: [] },
} as const

export type ResourceName = keyof typeof resourceConfig

export const adminNav = [
  { heading: 'Overview', items: [{ key: 'dashboard', title: 'Overview' }, { key: 'users', title: 'Users' }, { key: 'token-requests', title: 'Token requests' }, { key: 'ledger', title: 'Token ledger' }] },
  { heading: 'Workspace', items: [{ key: 'projects', title: 'Projects' }, { key: 'competitors', title: 'Competitors' }, { key: 'sources', title: 'Sources' }, { key: 'products', title: 'Products' }, { key: 'website-pages', title: 'Website pages' }, { key: 'instagram-posts', title: 'Instagram posts' }] },
  { heading: 'Analysis', items: [{ key: 'gaps', title: 'Gaps' }, { key: 'strategies', title: 'Strategies' }, { key: 'reviews', title: 'Reviews' }, { key: 'documents', title: 'Documents' }, { key: 'suggestions', title: 'Suggestions' }] },
  { heading: 'Operations', items: [{ key: 'integrations', title: 'Integrations' }, { key: 'contacts', title: 'Contact messages' }] },
] as const
