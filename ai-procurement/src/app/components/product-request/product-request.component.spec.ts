import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProductRequestComponent } from './product-request.component';

describe('ProductRequestComponent', () => {
  let component: ProductRequestComponent;
  let fixture: ComponentFixture<ProductRequestComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductRequestComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProductRequestComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
