const FilterComponent = {
   template: '#filter-component',
   props: {
      'country': { type: String, required: false, default: "" },
      'category': { type: Number, required: false, default: null },
      'search': { type: String, required: false, default: "" },
      'sort': { type: Number, required: true },
      'countries': { type: Array, required: true },
      'categories': { type: Array, required: true },
      'updateFilters': { type: Function, required: true },
      'updateSorts': { type: Function, required: true }
   },
   methods: {
      reset() {
         this.updateFilters();
      },
      update_sorts(sort, event) {
         if (event.target.checked && sort != 'none') {
            sort = [sort].concat(GlobalStore.sorts);
         } else {
            sort = GlobalStore.sorts;
         }
         this.updateSorts(sort)
      },
      update_filters(type, event) {
         let value;
         if (type == 'country') {
            value = event.target.value;
         } else if (type == 'category') {
            value = event.target.value != "" ? Number(event.target.value) : null;
         } else if (type == 'search') {
            value = event.target.value;
         } else if (type == 'is_new') {
            value = event.target.checked;
         } else if (type == 'single_only') {
            value = event.target.checked;
         } else if (type == 'sale_only') {
            value = event.target.checked;
         }

         this.updateFilters({ 
            ...{ 
               'country': this.country, 
               'category': this.category, 
               'search': this.search,
            }, 
            [type]: value 
         });
      },
   }
};
