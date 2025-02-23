# Application Guidelines

## Frontend Architecture

The frontend uses React, TypeScript, and Vite with modern best practices.

### Styling Guidelines

#### CSS Framework
- Tailwind CSS and Shad CN with modern utility classes
- Component-first approach

#### Design Principles
1. Consistent spacing using Tailwind's spacing scale
2. Use semantic color names from the Tailwind palette
3. Responsive design using Tailwind's breakpoint system

### Component Structure
- Keep components small and focused
- Use composition over inheritance
- Implement proper type safety with TypeScript

## Best Practices

1. Use modern React patterns
   - Hooks for state management
   - Context for global state
   - Suspense for data loading

2. Implement proper error boundaries
   - Handle UI errors gracefully
   - Provide meaningful error messages

3. Follow accessibility guidelines
   - Semantic HTML
   - ARIA labels where needed
   - Keyboard navigation support

4. Optimize for performance
   - Code splitting
   - Lazy loading
   - Memoization when appropriate