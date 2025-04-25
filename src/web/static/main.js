const GlobalStore = {
   max_score: 0,
   sorts: ['-combined_score']
};

const categoryImageMap = Object.freeze({
   'Wine': '/static/img/wine.png',
   'Beer': '/static/img/beer.png',
   'Coolers & Ciders': '/static/img/beer.png',
   'Spirits': '/static/img/liquor.png',
   'Liquor': '/static/img/liquor.png',
});

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
      'search': {
         type: String,
         required: false,
         default: "",
      },
      'sort': {
         type: Number,
         required: true,
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
      },
      'updateSorts': {
         type: Function,
         required: true
      }
   },
   template: '#filter-component',
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
         console.log(type, event);
         if (type == 'country') {
            value = event.target.value;
         } else if (type == 'category') {
            value = event.target.value != "" ? Number(event.target.value) : null;
         } else if(type == 'search') {
            value = event.target.value;
         } else if(type == 'is_new'){
            value = event.target.checked;
         }

         this.updateFilters({ ...{ 'country': this.country, 'category': this.category, 'search': this.search }, [type]: value });
      },
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
         max_score: 0,  // Initialize to 0
      };
   },
   async mounted() {
      this.max_score = GlobalStore.max_score;  // Set the value after component is mounted
      document
         .getElementById('modalDialog')
         .addEventListener('click', this.close);

      document.body.classList.add('modal-is-opening');

      setTimeout(() => {
         document.body.classList.remove('modal-is-opening');
         document.body.classList.add('modal-is-open');
      }, 300);

      data = await this.fetchData(this.product.sku);
      dateLabels = data.map(entry => new Date(entry.last_updated));
      priceData = data.map(entry => entry.price);
      boozeScoreData = priceData.map((price) => {
         const price_per_ml = price / (this.product.volume * 1000 * this.product.unit_size)
         return Math.round((1 / price_per_ml) * (this.product.alcohol + 1));
      });

      let delayed;
      const ctx = this.$refs.myChart.getContext('2d');
      new Chart(ctx, {
         type: 'line',
         data: {
            labels: dateLabels,
            datasets: [{
               label: 'Price',
               data: priceData,
               borderColor: '#82ab00',
               backgroundColor: '#202632',
               fill: false,
               pointHoverRadius: 5,
               yAxisID: 'y',
            }, {
               label: 'Boozescore',
               data: boozeScoreData,
               borderColor: '#802632',
               backgroundColor: '#202632',
               fill: false,
               pointHoverRadius: 5,
               yAxisID: 'y1',
            }]
         },
         options: {
            animation: {
               onComplete: () => {
                  delayed = true;
               },
               delay: (context) => {
                  let delay = 0;
                  if (context.type === 'data' && context.mode === 'default' && !delayed) {
                     delay = context.dataIndex * 30 + context.datasetIndex * 10;
                  }
                  return delay;
               },
            },
            plugins: {
               legend: {
                  display: true
               }
            },
            scales: {
               x: {
                  type: 'time',
                  title: {
                     display: true,
                     text: 'Date'
                  }
               },
               y: {
                  title: {
                     display: true,
                     text: 'Price'
                  },
                  ticks: {
                     callback: function (value) {
                        return '$' + value.toFixed(2); // Format y-axis ticks to 2 decimal places
                     }
                  },
                  scaleLabel: {
                     display: true,
                     labelString: 'Price ($)'
                  },
                  position: 'left',
               },
               y1: {
                  display: true,
                  position: 'right',
                  ticks: {
                     precision: 0,
                     callback: (value) => value.toLocaleString()
                  }
               }
            }
         }
      });
   },
   beforeUnmount() {
      document
         .getElementById('modalDialog')
         .removeEventListener('click', this.close);
   },
   methods: {
      async fetchData(sku) {
         try {
            const response = await fetch(`/api/price/${sku}`);
if (!response.ok) {
               throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
         } catch (error) {
            console.error('Error fetching data:', error);
         }
      },
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
      renderImage() {
         return this.product.image.replace('height400', 'height800');
      }
   },
};

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
            search: '',
         },
         sorts: [...GlobalStore.sorts],
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

      //const filteredData = this.products.filter((item) => item.combined_score >= 1000);
      //this.groupedProducts = this.groupAndSort(filteredData, 'category', this.sorts, 1000);
      this.filter();
      this.countries = this.getCountries(this.products);
      this.categories = this.getCategories(this.products);
   },
   created() {
      this.getQueryParams();
   },
   methods: {
      getQueryParams() {
         const params = new URLSearchParams(window.location.search);
         this.filters.category = params.get('category') || null;
         this.filters.country = params.get('country') || null;
         this.filters.search = params.get('search') || null;
      },
      updateQueryParams() {
         const params = new URLSearchParams();
         if (this.filters.category) {
            params.set('category', this.filters.category);
         }
         if (this.filters.country) {
            params.set('country', this.filters.country);
         }
         if(this.filters.search) {
            params.set('search', this.filters.search);
         }
         const newUrl = `${window.location.pathname}?${params.toString()}`;
         window.history.replaceState({}, '', newUrl);
      },
      openModal(product) {
         this.selectedProduct = product;
         this.isModalOpen = true;
      },
      closeModal() {
         this.isModalOpen = false;
      },
      async loadData() {
         //const storedData = LZString.decompress(localStorage.getItem('ProductData'));
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

            //localStorage.setItem('ProductData', LZString.compress(dataToStore));
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
         this.filters = { ...{ "country": "", "category": "", "search": "" }, ...this.filters, [type]: id };
         this.updateQueryParams();
         this.filter();
      },
      updateFilters(filters = {}) {
         console.log('Update filters', filters, this.sorts);
         this.filters = filters;
         this.updateQueryParams();
         this.filter();
      },
      updateSorts(sorts = GlobalStore.sorts) {
         console.log('Update sorts', sorts);
         this.sorts = sorts;
         this.filter();
      },
      filter() {
         console.log(this.filters);
         var filteredProducts = this.products.filter((x) => {
            let result = true;
            const filters = this.filters;

            if (filters.category) {
               result = result && x.full_category.some((category) => category.id == filters.category);
            }
            if (filters.country) {
               result = result && x.country.code == filters.country;
            }
            if (filters.search) {
               const query = filters.search.toLowerCase();
               result = result && (
                  x.name.toLowerCase().includes(query) ||
                  x.full_category.some((category) => category.description.toLowerCase().includes(query)) ||
                  x.upc.startsWith(query, 1)
               );
            }
            if (filters.is_new) {
               result = result && x.is_new;
            }
            return result;
         });

         if (this.products.length == filteredProducts.length)
            filteredProducts = filteredProducts.filter((item) => item.combined_score >= 1000);

         this.groupedProducts = this.groupAndSort(filteredProducts, 'category', this.sorts, 10000);
      },
      groupAndSort(data, groupByField, sortByFields, topN) {
         // Step 2: Group by the specified field
         const groupedData = data
            .filter((x) => x.price) // Make sure all items have price provided
            .reduce((acc, item) => {
               const key = item[groupByField];
               if (!acc[key]) {
                  acc[key] = [];
               }

               acc[key].push({
                  ...item,
                  url: this.get_url(item.sku),
                  image: this.get_image(item.sku),
                  price_drop: item.price.price - item.price.sale_price,
                  price_drop_rate: (item.price.price - item.price.sale_price) / item.price.price,
                  actual_country: window.UPC.getCountryFromUPC(item.upc),
               });
               return acc;
            }, {});

         // Step 3: Sort each group by the specified field and take top N results
         const result = Object.keys(groupedData).map(key => {
            const sortedGroup = groupedData[key]
               .sort(this.dynamicSort(sortByFields))
               //.sort((a, b) => b[sortByField] - a[sortByField])
               .slice(0, topN);

            return {
               [groupByField]: key,
               items: sortedGroup
            };
         });

         // Step 4: Sort the final results by the highest sortByField value in each group
         const sortedResult = result.sort((a, b) => {
            const maxA = Math.max(...a.items.map(item => item[sortByFields[sortByFields.length-1]]));
            const maxB = Math.max(...b.items.map(item => item[sortByFields[sortByFields.length-1]]));
            return maxB - maxA; // Sort in descending order
         });

         return sortedResult;
      },
      get_url: (sku) => `https://www.bcliquorstores.com/product/${sku}`,
      get_image: (sku) => `https://www.bcliquorstores.com/sites/default/files/imagecache/height400px/${sku}.jpg`,
      dynamicSort: (fields) => {
         return function (a, b) {
            for (let i = 0; i < fields.length; i++) {
               let field = fields[i];
               let order = 1;

               // Check for descending order if specified
               if (field[0] === '-') {
                  order = -1;
                  field = field.substring(1);
               }

               // Compare the two values
               if (a[field] < b[field]) {
                  return -1 * order;
               } else if (a[field] > b[field]) {
                  return 1 * order;
               }
            }

            // If all fields are equal
            return 0;
         };
      }
   }
});

// Mount the app to the #app div
app.mount('#app');
