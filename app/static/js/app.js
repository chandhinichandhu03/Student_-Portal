(function(){
	const btn = document.getElementById('themeBtn');
	if(btn){
		btn.addEventListener('click', () => {
			document.body.classList.toggle('dark');
			btn.textContent = document.body.classList.contains('dark') ? 'Light' : 'Dark';
		});
	}
})();
