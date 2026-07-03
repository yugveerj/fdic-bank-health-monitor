<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<!-- neverShowQueries: production viewers get results, not SQL chips -->
<EvidenceDefaultLayout {data} neverShowQueries={true}>
	<slot slot="content" />
</EvidenceDefaultLayout>
