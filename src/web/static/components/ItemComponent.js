const ItemComponent = {
   props: {
      'item': {
         type: Object,
         required: true
      }
   },
   template: '#item-component',
   methods: {
      handleImageError(event, category) {
         event.target.src = categoryImageMap[category] || categoryImageMap['Liquor'];
      },
      printDate(dateString) {
         const options = { month: 'short', day: '2-digit' };
         const formatter = new Intl.DateTimeFormat('en-US', options);

         return formatter.format(new Date(dateString));
      },
      filter(type, id) {
         this.$emit('onFilter', type, id);
      },
      select(product) {
         console.log('select', product);
         this.$emit('onSelect', product);
      },
   }
};
