// '.picture img' on mobile devices
var imageDeviceWidth = 478;
	
// Resizing '#textFader h1' throughtout width change
var textFaderDeviceWidth = 768;


// Shows image on approtpriate width change
var showImageIfAppropriate = function showImageIfAppropriate() {
	// console.log('$(window).width():', $(window).width());

	if($(window).width() <= textFaderDeviceWidth) {
		$('.picture img').fadeTo('slow', 1);
	} else {
		$('.picture img').hide();
	}
};

// Text resize on approtpriate width change
var resizeTextIfAppropriate = function resizeTextIfAppropriate() {

	if($(window).width() < imageDeviceWidth) {
		$('#textFader h1').animate(
			{fontSize: '80px', margin: '0px 10px'},
			{duration: 500, queue: false});
	} else {
		$('#textFader h1').animate(
			{fontSize: '140px'},
			{duration: 500, queue: false});
	}
};

// Fades in front elements
$(document).ready(function() {
        $('#headline, #socialMedia').fadeTo('slow', 0.2);
        $('#headline, #socialMedia').fadeTo('slow', 1);

        showImageIfAppropriate();
        resizeTextIfAppropriate();
 });

$(window).resize(function() {
	showImageIfAppropriate();
	resizeTextIfAppropriate();
});

	// Get ID 'videoBackgroundContainer'
	var videoElement = document.getElementById('videoBackgroundContainer');

	document.addEventListener('visibilitychange', function() {
		// Pause background video when page is hidden
		if (document.hidden) {     
		$('#videoBackgroundContainer').animate({volume: 0}, 1000, 'linear', function() {
		videoElement.pause();
	});
		// Play background video when page is shown
		} else {
		videoElement.play();  
		$('#videoBackgroundContainer').animate({volume: 1}, 1000, 'linear');
		} 
	});