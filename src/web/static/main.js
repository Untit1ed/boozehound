GlobalStore = {
   max_score: 0
};

categoryImageMap = {
   'Wine': '/static/img/wine.png',
   'Beer': '/static/img/beer.png',
   'Coolers & Ciders': '/static/img/beer.png',
   'Spirits': '/static/img/liquor.png',
   'Liquor': '/static/img/liquor.png',
};

const FilterComponent = {
   props: {
      'country': {
         type: String,
         required: false,
         default: "",
      },
      'category': {
         type: Number,
         required: false,
         default: null,
      },
      'countries': {
         type: Array,
         required: true
      },
      'categories': {
         type: Array,
         required: true
      },
      'updateFilters': {
         type: Function,
         required: true
      }
   },
   template: '#filter-component',
   methods: {
      reset() {
         this.updateFilters();
      },
      update(type, event) {
         if (type == 'country') {
            value = event.target.value;
         } else if (type == 'category') {
            value = event.target.value != "" ? Number(event.target.value) : null;
         }

         this.updateFilters({ ...{ 'country': this.country, 'category': this.category }, [type]: value });
      }
   }
};

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

const ModalComponent = {
   template: '#modal-component',
   props: {
      product: {
         type: Object,
         required: true,
      },
   },
   data() {
      return {
         max_score: GlobalStore.max_score,
      };
   },
   mounted() {
      document
         .getElementById('modalDialog')
         .addEventListener('click', this.close);

      document.body.classList.add('modal-is-opening');

      setTimeout(() => {
         document.body.classList.remove('modal-is-opening');
         document.body.classList.add('modal-is-open');
      }, 300);
   },
   beforeUnmount(){
      document
         .getElementById('modalDialog')
         .removeEventListener('click', this.close);
   },
   methods: {
      handleImageError(event, category) {
         event.target.src = categoryImageMap[category] || categoryImageMap['Liquor'];
      },
      close() {
         document.body.classList.add('modal-is-closing');
         document.body.classList.remove('modal-is-open');

         setTimeout(() => {
            document.body.classList.remove('modal-is-closing');
            this.$emit("onClose");
         }, 300);
      },
      renderImage(){
         return this.product.image.replace('height400', 'height800');
      }
   },
};

// Create the Vue app
const app = Vue.createApp({
   components: {
      ItemComponent,
      FilterComponent,
      ModalComponent,
   },
   data() {
      return {
         products: [],
         countries: [],
         categories: [],
         groupedProducts: [],
         filters: {
            country: '',
            category: null,
         },
         loading: true,
         isModalOpen: false,
         selectedProduct: null,
      };
   },
   async mounted() {
      await this.loadData();

      if (!this.products.length)
         return;

      GlobalStore.max_score = this.products[0].combined_score;

      const filteredData = this.products.filter((item) => item.combined_score >= 1000);
      this.groupedProducts = this.groupAndSort(filteredData, 'category', 'combined_score', 1000);
      this.countries = this.getCountries(this.products);
      this.categories = this.getCategories(this.products);
   },
   methods: {
      openModal(product){
         this.selectedProduct = product;
         this.isModalOpen = true;
      },
      closeModal() {
         this.isModalOpen = false;
      },
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
            this.setProducts(data.products);
         }
      },
      getCountries(products) {
         const countriesSet = new Set();

         return products
            .reduce((acc, item) => {
               const { name, code } = item.country;
               if (!countriesSet.has(code)) {
                  countriesSet.add(code);
                  acc.push({ name, code });
               }
               return acc;
            }, [])
            .sort((a, b) => a.name.localeCompare(b.name));
      },
      getCategories(products) {
         const groupedCategories = {};

         products.forEach(product => {
            const [cat, subCat, subSubCat] = product.full_category;

            // Initialize the main category if it doesn't exist
            if (!groupedCategories[cat.id]) {
               groupedCategories[cat.id] = {
                  id: cat.id,
                  description: cat.description,
                  subcategories: {}
               };
            }

            // Initialize the subcategory if it doesn't exist
            if (!groupedCategories[cat.id].subcategories[subCat.id]) {
               groupedCategories[cat.id].subcategories[subCat.id] = {
                  id: subCat.id,
                  description: `- ${subCat.description}`,
                  subSubcategories: {}
               };
            }

            // Initialize the sub-subcategory if it doesn't exist
            if (!groupedCategories[cat.id].subcategories[subCat.id].subSubcategories[subSubCat.id]) {
               groupedCategories[cat.id].subcategories[subCat.id].subSubcategories[subSubCat.id] = {
                  id: subSubCat.id,
                  description: `-- ${subSubCat.description}`
               };
            }
         });

         function flattenObject(obj) {
            const result = [];

            function recurse(current) {
               if (current.id && current.description) {
                  result.push({ id: current.id, description: current.description });
               }

               // Flatten subcategories
               Object.values(current.subcategories || {}).forEach(subCat => {
                  recurse(subCat);
                  // Flatten sub-subcategories within each subcategory
                  Object.values(subCat.subSubcategories || {}).forEach(subSubCat => recurse(subSubCat));
               });
            }

            Object.values(obj).forEach(recurse);
            return result;
         }

         return flattenObject(groupedCategories);
      },
      setProducts(dataToStore) {
         this.products = dataToStore
         this.loading = false;
      },
      setFilter(type, id) {
         this.filters = { ...{ "country": "", "category": "" }, ...this.filters, [type]: id };
         this.filter();
      },
      updateFilters(filters = {}) {
         console.log('Update filters', filters);
         this.filters = filters;
         this.filter();
      },
      filter() {
         console.log(this.filters);
         var filteredProducts = this.products.filter((x) => {
            result = true;

            for (filter_type in this.filters) {
               if (!this.filters[filter_type])
                  continue;

               if (filter_type == 'category')
                  result = result && x.full_category.some((category) => category.id == this.filters[filter_type]);
               if (filter_type == 'country')
                  result = result && x.country.code == this.filters[filter_type];
            }

            return result;
         });

         if (this.products.length == filteredProducts.length)
            filteredProducts = filteredProducts.filter((item) => item.combined_score >= 1000);

         this.groupedProducts = this.groupAndSort(filteredProducts, 'category', 'combined_score', 1000);
      },
      groupAndSort(data, groupByField, sortByField, topN) {
         // Step 2: Group by the specified field
         const groupedData = data.filter((x) => x.price).reduce((acc, item) => {
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
