const ProgressBar = {
   props: {
      value: Number,
   },
   data() {
      return {
         max: GlobalStore.max_score,
      }
   },
   computed: {
      percentage() {
         return GlobalStore.max_score ? Math.round((this.value / this.max) * 100) : 0;
      },
      barStyle() {
         return {
            width: this.percentage + '%',
         };
      },
   },
   template: `
      {{ percentage }}% ({{ value.toLocaleString() }} / {{ max.toLocaleString() }})
      <div style="width: 100%; background: #0003; border-radius: 10px; overflow: hidden; height: 20px; position: relative;">
        <div :style="barStyle" style="height: 100%; background: #82ab00;">
        </div>
      </div>
  `,
};


const ModalComponent = {
   components: {
      ProgressBar
   },
   template: '#modal-component',
   props: {
      product: {
         type: Object,
         required: true,
      },
   },
   async mounted() {
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
