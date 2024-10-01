categoryImageMap = {
   'Wine': '/static/img/wine.png',
   'Beer': '/static/img/beer.png',
   'Coolers & Ciders': '/static/img/beer.png',
   'Spirits': '/static/img/liquor.png',
   'Liquor': '/static/img/liquor.png',
};

const FilterComponent = {
   props: {
      'filters': {
         type: Object,
         required: true
      },
      'resetFilters': {
         type: Function,
         required: true
      }
   },
   template: '#filter-component',
   methods: {
      reset() {
         this.resetFilters();
      }
   }
};

const ItemComponent = {
   props: {
      'item': {
         type: Object,
         required: true
      }, 'index': {
         type: Number,
         required: true
      }, 'onFilter': {
         type: Function,
         required: true
      }
   },
   template: '#item-component',
   methods: {
      handleImageError(event, category) {
         event.target.src = categoryImageMap[category] || categoryImageMap['Liquor'];
      },
      getCurrentImage(product) {
         return product.isHovered ? product.image.replace('height400', 'height800') : product.image;
      },
      changeImage(product, isHover) {
         product.isHovered = isHover;
      },
      printDate(dateString) {
         const options = { month: 'short', day: '2-digit' };
         const formatter = new Intl.DateTimeFormat('en-US', options);

         return formatter.format(new Date(dateString));
      },
      filter(type, id) {
         this.onFilter(type, id);
      }
   }
};

// Create the Vue app
const app = Vue.createApp({
   components: {
      'filter-component': FilterComponent,
      'item-component': ItemComponent
   },
   data() {
      return {
         products: [],
         categories: [],
         filters: {},
         loading: true
      };
   },
   async mounted() {
      await this.loadData();

      if (!this.products.length)
         return;

      this.categories = this.groupAndSort(this.products, 'category', 'combined_score', 100);
   },
   methods: {
      async loadData() {
         const storedData = localStorage.getItem('ProductData');

         var storedDataOject = { products: [] };
         if (storedData) {
            try {
               storedDataOject = JSON.parse(storedData);
               if (storedDataOject.timestamp) {
                  const now = new Date().getTime();
                  const timestamp = parseInt(storedDataOject.timestamp, 10);
                  const thirtyMinutes = 30 * 60 * 1000;

                  if (
                     now - timestamp < thirtyMinutes &&
                     storedDataOject.products &&
                     storedDataOject.products.length > 0
                  ) {
                     console.log('Cached.')
                     this.setProducts(storedDataOject.products);
                     return;
                  }
               }
            } catch (error) {
               console.error("Invalid data in cache.", error);
            }
         }

         await this.fetchData(storedDataOject);
      },
      async fetchData(data) {
         try {
            const response = await fetch('/api/data');
            data = await response.json();

            const dataToStore = JSON.stringify({
               products: data.products,
               timestamp: new Date().getTime()
            });

            localStorage.setItem('ProductData', dataToStore);
            console.log('Fetched.')

         } catch (error) {
            console.error('Error fetching data:', error);
         } finally {
            console.log("Setting products...");
            this.setProducts(data.products)
         }
      },
      setProducts(dataToStore) {
         this.products = dataToStore
         this.loading = false;
      },
      filter(type, id) {
         this.filters = { ...this.filters, [type]: id };
         console.log(this.filters);
         const filteredProducts = this.products.filter((x) => {
            result = true;

            for(filter_type in this.filters){
               if (filter_type == 'category')
                  result = result && x.full_category.some((category) => category.id == this.filters[filter_type]);
               if (filter_type == 'country')
                  result = result && x.country.code == this.filters[filter_type];
            }

            return result;
         });
         this.categories = this.groupAndSort(filteredProducts, 'category', 'combined_score', 100);
      },
      resetFilters() {
         this.filters = {};
         this.categories = this.groupAndSort(this.products, 'category', 'combined_score', 100);
      },
      groupAndSort(data, groupByField, sortByField, topN) {
         // Step 1: Filter data based on combined_score
         const filteredData = data.filter((item) => item.combined_score >= 1000);
         // Step 2: Group by the specified field
         const groupedData = filteredData.reduce((acc, item) => {
            const key = item[groupByField];
            if (!acc[key]) {
               acc[key] = [];
            }
            acc[key].push(item);
            return acc;
         }, {});

         // Step 3: Sort each group by the specified field and take top N results
         const result = Object.keys(groupedData).map(key => {
            const sortedGroup = groupedData[key]
               .sort((a, b) => b[sortByField] - a[sortByField])
               .slice(0, topN);

            return {
               [groupByField]: key,
               items: sortedGroup
            };
         });

         // Step 4: Sort the final results by the highest sortByField value in each group
         const sortedResult = result.sort((a, b) => {
            const maxA = Math.max(...a.items.map(item => item[sortByField]));
            const maxB = Math.max(...b.items.map(item => item[sortByField]));
            return maxB - maxA; // Sort in descending order
         });

         return sortedResult;
      },
   }
});

// Mount the app to the #app div
app.mount('#app');
