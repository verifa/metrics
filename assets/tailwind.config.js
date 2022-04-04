
tailwind.config = {
    theme: {
        fontFamily: {
            sans: ['Outfit', 'sans-serif'],
        },
        extend: {
            colors: {
                'v-black': "#0d0e12",
                'v-pink': "#fc9cac",
                'v-green': "#ccecef",
                'v-gray': "#c4d0dd",
                'v-lilac': "#ad9ce3",
                'v-beige': "#8f8379",
                'v-white': "#f9fafb",
            },
        }
    }
}

// Insert the Tailwind config as a style.
// This is a bit hacky but not sure how else to add a <style> block
document.head.insertAdjacentHTML("beforeend", `
<style type="text/tailwindcss">
@layer base {
    h1, h2, h3, h4, h5, h6, p, li {
        @apply text-v-black break-words;
    }
    h1, h2, h3, h4, h5, h6 {
        @apply font-bold;
    }

    h1 {
        @apply text-5xl leading-tight sm:text-6xl sm:leading-tight md:text-7xl md:leading-tight;
        @apply mb-8;
    }
    h2 {
        @apply text-4xl leading-tight sm:text-5xl sm:leading-tight md:text-6xl md:leading-tight;
        @apply mb-8;
    }
    h3 {
        @apply text-3xl md:text-4xl md:leading-snug;
        @apply mb-8;
    }
    h4 {
        @apply text-2xl md:leading-relaxed;
        @apply mb-6;
    }
    h5 {
        @apply text-xl leading-relaxed;
        @apply mb-8;
    }
    h6 {
        @apply text-lg leading-relaxed;
        @apply mb-8;
    }

    body {
        @apply bg-v-white;
    }
    main {
        @apply bg-v-white mx-auto max-w-7xl px-8 sm:px-16;
    }
    section, article {
        @apply mb-20 md:mb-24 lg:mb-32;
    }
}
</style>
`)