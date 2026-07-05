<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	import { onMount } from 'svelte';
	export let data;

	// GA4 property "FDIC Bank Health Monitor"; events documented in
	// docs/event_dictionary.md. Loaded only on the production host so local
	// dev and previews send nothing.
	const GA_ID = 'G-44RCFYRK9W';

	onMount(() => {
		if (window.location.hostname !== 'yugveerj.github.io') return;

		const s = document.createElement('script');
		s.async = true;
		s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
		document.head.appendChild(s);
		window.dataLayer = window.dataLayer || [];
		window.gtag = function () {
			window.dataLayer.push(arguments);
		};
		window.gtag('js', new Date());
		window.gtag('config', GA_ID);

		// Custom events, delegated so prerendered links on every page are covered.
		// Capture phase because the dropdown library closes its popover on this
		// same click, and the open trigger is what names the dropdown.
		document.addEventListener(
			'click',
			(e) => {
				const target = e.target instanceof Element ? e.target : null;
				if (!target) return;

				const opt = target.closest('[role="option"]');
				if (opt) {
					const trigger = document.querySelector('button[role="combobox"][data-state="open"]');
					const title = trigger ? trigger.textContent : '';
					const value = opt.getAttribute('data-value') ?? opt.textContent.trim();
					if (title.includes('Institution')) window.gtag('event', 'bank_selected', { bank: value });
					else if (title.includes('Metric')) window.gtag('event', 'metric_selected', { metric: value });
					return;
				}

				const link = target.closest('a[href]');
				if (!link) return;
				if (link.href.includes('public.tableau.com')) window.gtag('event', 'tableau_click');
				else if (
					link.href.includes('datastudio.google.com') ||
					link.href.includes('lookerstudio.google.com')
				)
					window.gtag('event', 'looker_click');
				else if (link.href.includes('latest.xlsx')) window.gtag('event', 'excel_download');
			},
			true
		);
	});
</script>

<!-- neverShowQueries: production viewers get results, not SQL chips -->
<EvidenceDefaultLayout {data} neverShowQueries={true}>
	<div slot="content">
		<slot />
		<footer class="mt-12 border-t pt-3 text-xs text-gray-400">
			Anonymous usage analytics (Google Analytics): page views and feature clicks. No personal
			data is collected.
		</footer>
	</div>
</EvidenceDefaultLayout>
