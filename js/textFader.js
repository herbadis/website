$(document).ready(function() {
  
  var $textFader = $('#textFader h1');

      $textFader.fadeIn(2000, function() { 
          unBlurElement(this);
      });

  }, {offset:700});

  function blurElement(element, size) {
        var filterVal = 'blur('+size+'px)';
        $(element).css({ 
          'filter': filterVal
        });
  }

  function unBlurElement(element) { 
      var filterVal = 'blur('+0+'px)';

      $(element).css({
        'filter': 'none'
      });
      
  }