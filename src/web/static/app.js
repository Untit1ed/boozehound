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
                  alt_image: this.get_alt_image(item.category),
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
      get_image: (sku) => `/image/height400/${sku}.jpg`,
      get_alt_image: (category) => categoryImageMap[category],
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
