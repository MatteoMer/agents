Your job is to port the React codebase in ./source to Vue 3 in ./target.

Make a commit and push your changes after every single file edit.

Use the .agent/ directory as a scratchpad:
- .agent/PLAN.md for your porting strategy
- .agent/TODO.md for tracking progress
- .agent/COMPONENT_MAP.md for mapping React components to Vue equivalents

Porting guidelines:

1. SETUP
   - Initialize Vue 3 project with Vite
   - Set up TypeScript support
   - Configure equivalent tooling (ESLint, Prettier)

2. COMPONENT MAPPING
   - React functional components -> Vue 3 <script setup> components
   - React hooks -> Vue 3 Composition API
     - useState -> ref() or reactive()
     - useEffect -> watch() or onMounted/onUnmounted
     - useContext -> provide/inject
     - useMemo -> computed()
     - useCallback -> not needed (Vue handles this)
   - React props -> Vue props with defineProps
   - React events -> Vue emits with defineEmits

3. STATE MANAGEMENT
   - React Context -> Vue provide/inject or Pinia
   - Redux/Zustand -> Pinia

4. ROUTING
   - React Router -> Vue Router

5. TESTING
   - Port tests using Vue Test Utils
   - Aim for 20% of your time on tests

When complete, verify:
1. All components render without errors
2. State management works correctly
3. Routing functions as expected
4. Tests pass
