// Create a global UPC namespace
window.UPC = {
   getCountryFromUPC: function (upc) {
      // Ensure the UPC is a string
      if (typeof upc !== 'string') {
         throw new Error('UPC must be a string');
      }

      // Extract the first three digits of the UPC
      const prefix = upc.substring(1, 4);

      // Define the GS1 prefix ranges and their corresponding country codes
      const gs1Prefixes = [
         { range: [0, 19], country: 'USA and Canada' }, // United States and Canada
         { range: [20, 29], country: 'Unknown' },   // Restricted distribution
         { range: [30, 39], country: 'United States' },   // United States
         { range: [40, 49], country: 'Unknown' },   // Used to issue restricted circulation numbers within a geographic region
         { range: [50, 59], country: 'Unknown' },   // Used to issue restricted circulation numbers within a geographic region
         { range: [60, 99], country: 'USA and Canada' }, // United States and Canada
         { range: [100, 139], country: 'United States' }, // United States and Canada
         { range: [200, 299], country: 'Unknown' }, // Restricted distribution
         { range: [300, 379], country: 'France and Monaco' }, // France and Monaco
         { range: [380, 380], country: 'Bulgaria' }, // Bulgaria
         { range: [383, 383], country: 'Slovenia' }, // Slovenia
         { range: [385, 385], country: 'Croatia' }, // Croatia
         { range: [387, 387], country: 'Bosnia and Herzegovina' }, // Bosnia and Herzegovina
         { range: [389, 389], country: 'Montenegro' }, // Montenegro
         { range: [400, 440], country: 'Germany' }, // Germany
         { range: [450, 459], country: 'Japan' }, // Japan
         { range: [460, 469], country: 'Russia' }, // Russia
         { range: [470, 470], country: 'Kyrgyzstan' }, // Kyrgyzstan
         { range: [471, 471], country: 'Taiwan' }, // Taiwan
         { range: [474, 474], country: 'Estonia' }, // Estonia
         { range: [475, 475], country: 'Latvia' }, // Latvia
         { range: [476, 476], country: 'Azerbaijan' }, // Azerbaijan
         { range: [477, 477], country: 'Lithuania' }, // Lithuania
         { range: [478, 478], country: 'Uzbekistan' }, // Uzbekistan
         { range: [479, 479], country: 'Sri Lanka' }, // Sri Lanka
         { range: [480, 480], country: 'Philippines' }, // Philippines
         { range: [481, 481], country: 'Belarus' }, // Belarus
         { range: [482, 482], country: 'Ukraine' }, // Ukraine
         { range: [484, 484], country: 'Moldova' }, // Moldova
         { range: [485, 485], country: 'Armenia' }, // Armenia
         { range: [486, 486], country: 'Georgia' }, // Georgia
         { range: [487, 487], country: 'Kazakhstan' }, // Kazakhstan
         { range: [489, 489], country: 'Hong Kong' }, // Hong Kong
         { range: [490, 499], country: 'Japan' }, // Japan
         { range: [500, 509], country: 'United Kingdom' }, // United Kingdom
         { range: [520, 520], country: 'Greece' }, // Greece
         { range: [528, 528], country: 'Lebanon' }, // Lebanon
         { range: [529, 529], country: 'Cyprus' }, // Cyprus
         { range: [530, 530], country: 'Albania' }, // Albania
         { range: [531, 531], country: 'North Macedonia' }, // North Macedonia
         { range: [535, 535], country: 'Malta' }, // Malta
         { range: [539, 539], country: 'Ireland' }, // Ireland
         { range: [540, 549], country: 'Belgium and Luxembourg' }, // Belgium and Luxembourg
         { range: [560, 560], country: 'Portugal' }, // Portugal
         { range: [569, 569], country: 'Iceland' }, // Iceland
         { range: [570, 579], country: 'Denmark' }, // Denmark
         { range: [590, 590], country: 'Poland' }, // Poland
         { range: [594, 594], country: 'Romania' }, // Romania
         { range: [599, 599], country: 'Hungary' }, // Hungary
         { range: [600, 601], country: 'South Africa' }, // South Africa
         { range: [603, 603], country: 'Ghana' }, // Ghana
         { range: [608, 608], country: 'Bahrain' }, // Bahrain
         { range: [609, 609], country: 'Mauritius' }, // Mauritius
         { range: [611, 611], country: 'Morocco' }, // Morocco
         { range: [613, 613], country: 'Algeria' }, // Algeria
         { range: [615, 615], country: 'Nigeria' }, // Nigeria
         { range: [616, 616], country: 'Kenya' }, // Kenya
         { range: [618, 618], country: 'Ivory Coast' }, // Ivory Coast
         { range: [619, 619], country: 'Tunisia' }, // Tunisia
         { range: [620, 620], country: 'Tanzania' }, // Tanzania
         { range: [621, 621], country: 'Syria' }, // Syria
         { range: [622, 622], country: 'Egypt' }, // Egypt
         { range: [623, 623], country: 'Brunei' }, // Brunei
         { range: [624, 624], country: 'Libya' }, // Libya
         { range: [625, 625], country: 'Jordan' }, // Jordan
         { range: [626, 626], country: 'Iran' }, // Iran
         { range: [627, 627], country: 'Kuwait' }, // Kuwait
         { range: [628, 628], country: 'Saudi Arabia' }, // Saudi Arabia
         { range: [629, 629], country: 'United Arab Emirates' }, // United Arab Emirates
         { range: [640, 649], country: 'Finland' }, // Finland
         { range: [690, 699], country: 'China' }, // China
         { range: [700, 709], country: 'Norway' }, // Norway
         { range: [729, 729], country: 'Israel' }, // Israel
         { range: [730, 739], country: 'Sweden' }, // Sweden
         { range: [740, 740], country: 'Guatemala' }, // Guatemala
         { range: [741, 741], country: 'El Salvador' }, // El Salvador
         { range: [742, 742], country: 'Honduras' }, // Honduras
         { range: [743, 743], country: 'Nicaragua' }, // Nicaragua
         { range: [744, 744], country: 'Costa Rica' }, // Costa Rica
         { range: [745, 745], country: 'Panama' }, // Panama
         { range: [746, 746], country: 'Dominican Republic' }, // Dominican Republic
         { range: [750, 750], country: 'Mexico' }, // Mexico
         { range: [754, 755], country: 'Canada' }, // Canada
         { range: [759, 759], country: 'Venezuela' }, // Venezuela
         { range: [760, 769], country: 'Switzerland' }, // Switzerland
         { range: [770, 771], country: 'Colombia' }, // Colombia
         { range: [773, 773], country: 'Uruguay' }, // Uruguay
         { range: [775, 775], country: 'Peru' }, // Peru
         { range: [777, 777], country: 'Bolivia' }, // Bolivia
         { range: [778, 779], country: 'Argentina' }, // Argentina
         { range: [780, 780], country: 'Chile' }, // Chile
         { range: [784, 784], country: 'Paraguay' }, // Paraguay
         { range: [786, 786], country: 'Ecuador' }, // Ecuador
         { range: [789, 790], country: 'Brazil' }, // Brazil
         { range: [800, 839], country: 'Italy' }, // Italy
         { range: [840, 849], country: 'Spain' }, // Spain
         { range: [850, 850], country: 'Cuba' }, // Cuba
         { range: [858, 858], country: 'Slovakia' }, // Slovakia
         { range: [859, 859], country: 'Czech Republic' }, // Czech Republic
         { range: [860, 860], country: 'Serbia' }, // Serbia
         { range: [865, 865], country: 'Mongolia' }, // Mongolia
         { range: [867, 867], country: 'North Korea' }, // North Korea
         { range: [868, 869], country: 'Turkey' }, // Turkey
         { range: [870, 879], country: 'Netherlands' }, // Netherlands
         { range: [880, 880], country: 'South Korea' }, // South Korea
         { range: [884, 884], country: 'Cambodia' }, // Cambodia
         { range: [885, 885], country: 'Thailand' }, // Thailand
         { range: [888, 888], country: 'Singapore' }, // Singapore
         { range: [890, 890], country: 'India' }, // India
         { range: [893, 893], country: 'Vietnam' }, // Vietnam
         { range: [896, 896], country: 'Pakistan' }, // Pakistan
         { range: [899, 899], country: 'Indonesia' }, // Indonesia
         { range: [900, 919], country: 'Austria' }, // Austria
         { range: [930, 939], country: 'Australia' }, // Australia
         { range: [940, 949], country: 'New Zealand' }, // New Zealand
         { range: [950, 950], country: 'Global Office' }, // Global Office
         { range: [955, 955], country: 'Malaysia' }, // Malaysia
         { range: [958, 958], country: 'Macau' }, // Macau
      ];

      // Iterate through the prefix ranges to find the matching country
      for (const { range, country } of gs1Prefixes) {
         const [start, end] = range;
         const prefixInt = parseInt(prefix, 10);
         if (prefixInt >= start && prefixInt <= end) {
            return "UPC: " + country;
         }
      }

      // Return null if no match is found
      return null;
   }
};
