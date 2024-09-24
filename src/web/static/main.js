categoryImageMap = {
   'Wine': '/static/img/wine.png',
   'Beer': '/static/img/beer.png',
   'Coolers & Ciders': '/static/img/beer.png',
   'Spirits': '/static/img/liquor.png',
   'Liquor': '/static/img/liquor.png',
};

// Define your Vue component
const ItemComponent = {
   props: ['item', 'index', 'getCategoryImage'],
   template: `
        <div class="category">
          <h2>{{ item.category }}</h2>
          <div class="grid item" v-for="(product, index) in item.items" :key="index">
               <div class="image-container">
                  <img :src="product.image" @error="handleImageError($event, product.category)" />
                  <span :class="'fi fi-' + product.country.toLowerCase()" class="fis"></span>
               </div>
               <div class="product-details">
                  <hgroup>
                     <p class="price">
                        <span v-if="product.sale_price !== product.price">
                          <s>\${{ product.price }}</s>
                          <mark>\${{ product.sale_price }}</mark>
                        </span>
                        <b v-else>\${{ product.price }}</b>
                     </p>
                     <p>
                        <a :href="product.url" target="blank">{{ product.name }}</a>
                     </p>
                  </hgroup>
                  <div>
                     <span>{{product.alcohol}}%</span>: <span>{{product.volume}}L</span> <span v-if="product.unit_size > 1">x {{product.unit_size}}</span>
                  </div>
                  <div>
                     <small>Boozecore: {{product.combined_score.toLocaleString()}}</small>
                  </div>
               </div>
          </div>
        </div>
      `,
   methods: {
      handleImageError(event, category) {
         console.log(category);
         event.target.src = categoryImageMap[category] || categoryImageMap['Liquor'];
      }
   }

};

// Create the Vue app
const app = Vue.createApp({
   components: {
      ItemComponent
   },
   data() {
      return {
         products: [],
         categories: [],
         loading: true
      };
   },
   async mounted() {
      await this.loadData();
      console.log("Setting categories...", this.products);
      if (this.products.length > 0) {
         console.log("Setting categories...");
         this.categories = this.groupAndSort(this.products, 'category', 'combined_score', 100);
      }
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
